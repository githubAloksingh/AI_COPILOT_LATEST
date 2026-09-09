package com.example.copilot.exception;

public class AiServiceQuotaExceededException extends RuntimeException {
    public AiServiceQuotaExceededException(String message, Throwable cause) {
        super(message, cause);
    }
}
