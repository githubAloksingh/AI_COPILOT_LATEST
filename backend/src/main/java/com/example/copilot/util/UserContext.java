package com.example.copilot.util;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/**
 * Authentication has been removed from the application.
 * This helper now resolves a friendly user name/role from the simple
 * {@code X-User-Name} / {@code X-User-Role} request headers so that
 * audit logging can still attribute actions. It does NOT perform any
 * authentication or authorization — everything is open.
 */
public class UserContext {

    public static String getCurrentUser() {
        String user = getHeader("X-User-Name");
        return (user == null || user.isBlank()) ? "User A" : user;
    }

    public static String getCurrentRole() {
        String role = getHeader("X-User-Role");
        return (role == null || role.isBlank()) ? "USER" : role.toUpperCase();
    }

    public static boolean isAdmin() {
        return "ADMIN".equalsIgnoreCase(getCurrentRole());
    }

    private static String getHeader(String name) {
        try {
            if (RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes attributes) {
                HttpServletRequest request = attributes.getRequest();
                return request.getHeader(name);
            }
        } catch (Exception ignored) {
            // No active request context (e.g. background thread) — fall back to defaults.
        }
        return null;
    }
}
