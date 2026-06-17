package com.arm.audit.repository;

import com.arm.audit.model.TrajectoryPoint;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TrajectoryPointRepository extends JpaRepository<TrajectoryPoint, Long> {

    List<TrajectoryPoint> findBySessionIdOrderByTimestampAsc(String sessionId);

    long deleteBySessionId(String sessionId);
}
