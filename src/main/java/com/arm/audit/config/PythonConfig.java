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
    private long timeoutSeconds = 45;
    private LlmConfig llm = new LlmConfig();

    @Data
    public static class LlmConfig {
        private String apiBase = "https://api.openai.com/v1";
        private String apiKey = "";
        private String model = "gpt-4o-mini";
    }
}
