package com.example.copilot.repository;

import com.example.copilot.entity.MockScreensJob;
import com.example.copilot.entity.MockScreensJobStatus;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface MockScreensJobRepository extends JpaRepository<MockScreensJob, Long> {
    @Query(value = "SELECT CURRENT_TIMESTAMP(6)", nativeQuery = true)
    java.time.LocalDateTime databaseNow();

    Optional<MockScreensJob> findByJobId(String jobId);

        Optional<MockScreensJob> findByIdempotencyKey(String idempotencyKey);

        @Lock(LockModeType.PESSIMISTIC_WRITE)
        @Query("select job from MockScreensJob job where job.id = :id")
        Optional<MockScreensJob> findByIdForUpdate(@Param("id") Long id);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    Optional<MockScreensJob> findFirstByStatusOrderByCreatedAtAscIdAsc(MockScreensJobStatus status);

        @Lock(LockModeType.PESSIMISTIC_WRITE)
        @Query("select job from MockScreensJob job where job.status in :statuses "
            + "and (job.leaseUntil is null or job.leaseUntil < :now) order by job.leaseUntil asc, job.id asc")
        List<MockScreensJob> findExpiredLeases(
            @Param("statuses") List<MockScreensJobStatus> statuses,
            @Param("now") LocalDateTime now,
            Pageable pageable);

        @Modifying
        @Query("update MockScreensJob job set job.leaseUntil = :leaseUntil "
            + "where job.id = :id and job.leaseToken = :leaseToken and job.status in :statuses")
        int extendLease(
            @Param("id") Long id,
            @Param("leaseToken") String leaseToken,
            @Param("statuses") List<MockScreensJobStatus> statuses,
            @Param("leaseUntil") LocalDateTime leaseUntil);
}