package com.arm.audit.service;

import com.arm.audit.config.PythonConfig;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class PythonBridgeService {

    private final PythonConfig pythonConfig;
    private final ObjectMapper objectMapper;

    public JsonNode analyzeTrajectory(List<Map<String, Object>> points) {
        try {
            ObjectNode input = objectMapper.createObjectNode();
            ArrayNode pointsArray = input.putArray("points");
            for (Map<String, Object> pt : points) {
                ObjectNode pointNode = pointsArray.addObject();
                pointNode.put("x", ((Number) pt.get("x")).doubleValue());
                pointNode.put("y", ((Number) pt.get("y")).doubleValue());
                pointNode.put("z", ((Number) pt.get("z")).doubleValue());
                Object ts = pt.get("timestamp");
                if (ts instanceof Number) {
                    pointNode.put("timestamp", ((Number) ts).doubleValue());
                } else {
                    pointNode.put("timestamp", 0.0);
                }
            }

            String jsonInput = objectMapper.writeValueAsString(input);

            ProcessBuilder pb = new ProcessBuilder(
                    pythonConfig.getExecutable(),
                    pythonConfig.getScriptPath()
            );
            pb.redirectErrorStream(true);

            Map<String, String> env = pb.environment();
            PythonConfig.LlmConfig llm = pythonConfig.getLlm();
            if (llm != null) {
                if (llm.getApiBase() != null && !llm.getApiBase().isEmpty()) {
                    env.put("LLM_API_BASE", llm.getApiBase());
                }
                if (llm.getApiKey() != null && !llm.getApiKey().isEmpty()) {
                    env.put("LLM_API_KEY", llm.getApiKey());
                }
                if (llm.getModel() != null && !llm.getModel().isEmpty()) {
                    env.put("LLM_MODEL", llm.getModel());
                }
            }

            Process process = pb.start();

            CompletableFuture<String> outputFuture = CompletableFuture.supplyAsync(() -> {
                try (InputStream is = process.getInputStream();
                     BufferedReader reader = new BufferedReader(
                             new InputStreamReader(is, StandardCharsets.UTF_8))) {
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        sb.append(line);
                    }
                    return sb.toString();
                } catch (IOException e) {
                    throw new CompletionException("Failed to read Python output", e);
                }
            });

            try (OutputStream os = process.getOutputStream()) {
                os.write(jsonInput.getBytes(StandardCharsets.UTF_8));
                os.flush();
            }

            boolean finished = process.waitFor(
                    pythonConfig.getTimeoutSeconds(), TimeUnit.SECONDS
            );

            if (!finished) {
                process.destroyForcibly();
                outputFuture.cancel(true);
                throw new RuntimeException("Python analysis timed out");
            }

            String output = outputFuture.get(10, TimeUnit.SECONDS);

            int exitCode = process.exitValue();
            if (exitCode != 0) {
                log.error("Python script exited with code {}: {}", exitCode, output);
                throw new RuntimeException("Python script failed with exit code " + exitCode);
            }

            return objectMapper.readTree(output);

        } catch (CompletionException e) {
            throw new RuntimeException(e.getCause().getMessage(), e.getCause());
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to execute Python analysis script", e);
            throw new RuntimeException("Python analysis execution failed", e);
        }
    }
}
