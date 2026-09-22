package com.example.copilot.repository;

import com.example.copilot.entity.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DocumentRepository extends JpaRepository<Document, Long> {
    List<Document> findByProjectIdOrderByCreatedAtDesc(Long projectId);
    List<Document> findByProjectIdAndFileNameOrderByCreatedAtDesc(Long projectId, String fileName);
    List<Document> findAllByOrderByCreatedAtDesc();

    @org.springframework.data.jpa.repository.Query("SELECT d.fileData FROM Document d WHERE d.id = :id")
    byte[] findFileDataById(@org.springframework.data.repository.query.Param("id") Long id);

    @org.springframework.data.jpa.repository.Modifying
    @org.springframework.transaction.annotation.Transactional
    @org.springframework.data.jpa.repository.Query("UPDATE Document d SET d.status = :status, d.errorMessage = :errorMessage, d.chunkCount = :chunkCount WHERE d.id = :id")
    void updateStatusAndChunkCount(
            @org.springframework.data.repository.query.Param("id") Long id,
            @org.springframework.data.repository.query.Param("status") String status,
            @org.springframework.data.repository.query.Param("errorMessage") String errorMessage,
            @org.springframework.data.repository.query.Param("chunkCount") Integer chunkCount
    );
}
