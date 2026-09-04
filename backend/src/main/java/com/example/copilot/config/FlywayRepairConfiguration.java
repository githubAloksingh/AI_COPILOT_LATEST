package com.example.copilot.config;

import org.flywaydb.core.Flyway;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.autoconfigure.flyway.FlywayMigrationStrategy;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Repairs Flyway schema-history checksums only when explicitly enabled for a
 * local development database. Production deployments retain Flyway's default
 * validation behaviour.
 */
@Configuration
public class FlywayRepairConfiguration {

    @Bean
    @ConditionalOnProperty(name = "copilot.flyway.repair-on-start", havingValue = "true")
    FlywayMigrationStrategy repairAndMigrate() {
        return FlywayRepairConfiguration::repairAndMigrate;
    }

    private static void repairAndMigrate(Flyway flyway) {
        flyway.repair();
        flyway.migrate();
    }
}
