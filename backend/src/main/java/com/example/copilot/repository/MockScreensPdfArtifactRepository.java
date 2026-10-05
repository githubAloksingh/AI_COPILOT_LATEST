package com.example.copilot.repository;

import com.example.copilot.entity.MockScreensPdfArtifact;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface MockScreensPdfArtifactRepository extends JpaRepository<MockScreensPdfArtifact, Long> {
    Optional<MockScreensPdfArtifact> findByMockScreensJobId(Long mockScreensJobId);
}