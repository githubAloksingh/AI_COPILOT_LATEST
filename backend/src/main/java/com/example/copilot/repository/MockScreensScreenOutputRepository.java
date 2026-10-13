package com.example.copilot.repository;

import com.example.copilot.entity.MockScreensScreenOutput;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface MockScreensScreenOutputRepository extends JpaRepository<MockScreensScreenOutput, Long> {
    List<MockScreensScreenOutput> findByMockScreensJobIdOrderBySequenceAsc(Long mockScreensJobId);
    long countByMockScreensJobId(Long mockScreensJobId);
}