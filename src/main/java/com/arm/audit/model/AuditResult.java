package com.arm.audit.model;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Entity
@Table(name = "audit_results")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String sessionId;

    @Column(nullable = false)
    private Boolean hasCollisionRisk;

    @Column(nullable = false)
    private Boolean hasJitterAnomaly;

    @Column
    private Double collisionRiskScore;

    @Column
    private Double jitterScore;

    @Column(length = 2000)
    private String details;

    @Column(length = 2000)
    private String rootCauseAnalysis;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = Instant.now();
    }
}
