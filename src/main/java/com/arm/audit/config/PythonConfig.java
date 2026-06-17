package com.arm.audit.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "audit.python")
public class PythonConfig {

    private String executable = "python3";
    private String scriptPath = "src/main/python/anomaly_detector.py";
    private long timeoutSeconds = 30;
}
