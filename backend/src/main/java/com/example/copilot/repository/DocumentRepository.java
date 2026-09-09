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
}
