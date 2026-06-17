package com.arm.audit.controller;

import com.arm.audit.dto.AuditResponseDto;
import com.arm.audit.dto.TrajectoryAuditRequest;
import com.arm.audit.service.TrajectoryAuditService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/audit")
@RequiredArgsConstructor
public class TrajectoryAuditController {

    private final TrajectoryAuditService trajectoryAuditService;

    @PostMapping("/trajectory")
    public ResponseEntity<AuditResponseDto> auditTrajectory(
            @Valid @RequestBody TrajectoryAuditRequest request) {
        AuditResponseDto response = trajectoryAuditService.auditTrajectory(request);
        return ResponseEntity.ok(response);
    }
}
