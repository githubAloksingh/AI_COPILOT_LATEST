package com.example.copilot.repository;

import com.example.copilot.entity.MockScreen;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface MockScreenRepository extends JpaRepository<MockScreen, Long> {

    List<MockScreen> findByGenerationIdOrderBySequenceAsc(Long generationId);

    @Query("SELECT s.imageData FROM MockScreen s WHERE s.id = :id")
    byte[] findImageDataById(@Param("id") Long id);
}
