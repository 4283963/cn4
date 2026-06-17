package com.arm.audit.repository;

import com.arm.audit.model.AuditResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AuditResultRepository extends JpaRepository<AuditResult, Long> {

    Optional<AuditResult> findTopBySessionIdOrderByCreatedAtDesc(String sessionId);

    List<AuditResult> findBySessionIdOrderByCreatedAtDesc(String sessionId);
}
