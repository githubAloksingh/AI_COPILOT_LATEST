package com.example.copilot.repository;

import com.example.copilot.entity.MockScreenGeneration;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface MockScreenGenerationRepository extends JpaRepository<MockScreenGeneration, Long> {

    Optional<MockScreenGeneration> findByJobId(String jobId);

    List<MockScreenGeneration> findByDocumentIdOrderByCreatedAtDesc(Long documentId);

    List<MockScreenGeneration> findAllByOrderByCreatedAtDesc();

    @Query("SELECT g.pdfData FROM MockScreenGeneration g WHERE g.id = :id")
    byte[] findPdfDataById(@Param("id") Long id);

    @Query("SELECT g.pdfData FROM MockScreenGeneration g WHERE g.jobId = :jobId")
    byte[] findPdfDataByJobId(@Param("jobId") String jobId);
}
