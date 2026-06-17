package com.arm.audit.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.time.Instant;

@Data
public class TrajectoryPointDto {

    @NotNull(message = "X coordinate is required")
    private Double x;

    @NotNull(message = "Y coordinate is required")
    private Double y;

    @NotNull(message = "Z coordinate is required")
    private Double z;

    @NotNull(message = "Timestamp is required")
    private Instant timestamp;
}
