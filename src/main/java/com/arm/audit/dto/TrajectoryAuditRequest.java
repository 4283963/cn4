package com.arm.audit.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.List;

@Data
public class TrajectoryAuditRequest {

    @NotBlank(message = "Session ID is required")
    private String sessionId;

    @NotEmpty(message = "Trajectory points must not be empty")
    private List<TrajectoryPointDto> points;
}
