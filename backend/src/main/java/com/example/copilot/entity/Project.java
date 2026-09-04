package com.example.copilot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "project")
@Getter
@Setter
public class Project extends BaseEntity {

    @Column(name = "project_name", nullable = false)
    private String projectName;

    @Column(name = "department", nullable = false)
    private String department;

    @Column(name = "project_owner", nullable = false)
    private String projectOwner;

    @Column(name = "created_by")
    private String createdBy = "System";

    @Column(name = "status", nullable = false)
    private String status = "ACTIVE";
}
