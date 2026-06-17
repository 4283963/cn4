package com.arm.audit.service;

import com.arm.audit.dto.AuditResponseDto;
import com.arm.audit.dto.TrajectoryAuditRequest;
import com.arm.audit.dto.TrajectoryPointDto;
import com.arm.audit.model.AuditResult;
import com.arm.audit.model.TrajectoryPoint;
import com.arm.audit.repository.AuditResultRepository;
import com.arm.audit.repository.TrajectoryPointRepository;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TrajectoryAuditService {

    private final TrajectoryPointRepository trajectoryPointRepository;
    private final AuditResultRepository auditResultRepository;
    private final PythonBridgeService pythonBridgeService;

    @Transactional
    public AuditResponseDto auditTrajectory(TrajectoryAuditRequest request) {
        String sessionId = request.getSessionId();
        log.info("Starting trajectory audit for session: {}", sessionId);

        List<TrajectoryPoint> savedPoints = persistTrajectoryPoints(sessionId, request.getPoints());
        log.info("Persisted {} trajectory points for session: {}", savedPoints.size(), sessionId);

        List<Map<String, Object>> pythonInput = buildPythonInput(savedPoints);
        JsonNode analysisResult = pythonBridgeService.analyzeTrajectory(pythonInput);

        AuditResponseDto response = buildResponse(sessionId, analysisResult);

        persistAuditResult(sessionId, analysisResult);

        log.info("Audit completed for session {}: collisionRisk={}, jitterAnomaly={}",
                sessionId, response.getHasCollisionRisk(), response.getHasJitterAnomaly());

        return response;
    }

    private List<TrajectoryPoint> persistTrajectoryPoints(
            String sessionId, List<TrajectoryPointDto> dtos) {
        List<TrajectoryPoint> entities = dtos.stream()
                .map(dto -> TrajectoryPoint.builder()
                        .sessionId(sessionId)
                        .x(dto.getX())
                        .y(dto.getY())
                        .z(dto.getZ())
                        .timestamp(dto.getTimestamp())
                        .build())
                .collect(Collectors.toList());
        return trajectoryPointRepository.saveAll(entities);
    }

    private List<Map<String, Object>> buildPythonInput(List<TrajectoryPoint> points) {
        return points.stream()
                .map(p -> {
                    Map<String, Object> map = new LinkedHashMap<>();
                    map.put("x", p.getX());
                    map.put("y", p.getY());
                    map.put("z", p.getZ());
                    map.put("timestamp", p.getTimestamp().toEpochMilli());
                    return map;
                })
                .collect(Collectors.toList());
    }

    private AuditResponseDto buildResponse(String sessionId, JsonNode result) {
        boolean hasCollisionRisk = result.path("has_collision_risk").asBoolean(false);
        boolean hasJitterAnomaly = result.path("has_jitter_anomaly").asBoolean(false);
        double collisionScore = result.path("collision_risk_score").asDouble(0.0);
        double jitterScore = result.path("jitter_score").asDouble(0.0);

        List<AuditResponseDto.AnomalyDetail> anomalies = new ArrayList<>();
        JsonNode anomaliesNode = result.path("anomalies");
        if (anomaliesNode.isArray()) {
            for (JsonNode node : anomaliesNode) {
                anomalies.add(AuditResponseDto.AnomalyDetail.builder()
                        .type(node.path("type").asText(""))
                        .pointIndex(node.path("pointIndex").asInt(0))
                        .description(node.path("description").asText(""))
                        .severity(node.path("severity").asDouble(0.0))
                        .build());
            }
        }

        String rootCause = null;
        JsonNode rootCauseNode = result.path("root_cause_analysis");
        if (!rootCauseNode.isNull() && !rootCauseNode.asText().isEmpty()) {
            rootCause = rootCauseNode.asText();
        }

        String message;
        if (!hasCollisionRisk && !hasJitterAnomaly) {
            message = "轨迹正常，未检测到碰撞风险或抖动异常";
        } else {
            List<String> issues = new ArrayList<>();
            if (hasCollisionRisk) issues.add("碰撞风险");
            if (hasJitterAnomaly) issues.add("抖动异常");
            message = "检测到异常: " + String.join(", ", issues);
        }

        return AuditResponseDto.builder()
                .sessionId(sessionId)
                .hasCollisionRisk(hasCollisionRisk)
                .hasJitterAnomaly(hasJitterAnomaly)
                .collisionRiskScore(collisionScore)
                .jitterScore(jitterScore)
                .anomalies(anomalies)
                .rootCauseAnalysis(rootCause)
                .message(message)
                .build();
    }

    private void persistAuditResult(String sessionId, JsonNode result) {
        String details = null;
        JsonNode anomaliesNode = result.path("anomalies");
        if (anomaliesNode.isArray() && anomaliesNode.size() > 0) {
            details = anomaliesNode.toString();
            if (details.length() > 2000) {
                details = details.substring(0, 1997) + "...";
            }
        }

        String rootCause = null;
        JsonNode rootCauseNode = result.path("root_cause_analysis");
        if (!rootCauseNode.isNull() && !rootCauseNode.asText().isEmpty()) {
            rootCause = rootCauseNode.asText();
            if (rootCause.length() > 2000) {
                rootCause = rootCause.substring(0, 1997) + "...";
            }
        }

        AuditResult auditResult = AuditResult.builder()
                .sessionId(sessionId)
                .hasCollisionRisk(result.path("has_collision_risk").asBoolean(false))
                .hasJitterAnomaly(result.path("has_jitter_anomaly").asBoolean(false))
                .collisionRiskScore(result.path("collision_risk_score").asDouble(0.0))
                .jitterScore(result.path("jitter_score").asDouble(0.0))
                .details(details)
                .rootCauseAnalysis(rootCause)
                .build();

        auditResultRepository.save(auditResult);
    }
}
