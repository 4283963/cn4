package com.arm.audit.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditResponseDto {

    private String sessionId;
    private Boolean hasCollisionRisk;
    private Boolean hasJitterAnomaly;
    private Double collisionRiskScore;
    private Double jitterScore;
    private List<AnomalyDetail> anomalies;
    private String rootCauseAnalysis;
    private String message;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AnomalyDetail {
        private String type;
        private Integer pointIndex;
        private String description;
        private Double severity;
    }
}
