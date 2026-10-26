package com.nova.history;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;

@WebServlet("/api/history")
public class HistoryApiServlet extends HttpServlet {
    private final ConversationRepository repository = new ConversationRepository();

    @Override public void init() throws ServletException {
        try { repository.initialize(); }
        catch (SQLException error) { throw new ServletException("Cannot initialize NOVA history database", error); }
    }

    @Override protected void doPost(HttpServletRequest request, HttpServletResponse response) throws IOException {
        request.setCharacterEncoding(StandardCharsets.UTF_8.name());
        String speaker = request.getParameter("speaker");
        String message = request.getParameter("message");
        if (!("You".equals(speaker) || "NOVA".equals(speaker)) || message == null || message.isBlank() || message.length() > 10000) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Expected speaker (You or NOVA) and a message up to 10000 characters.");
            return;
        }
        try {
            repository.save(speaker, message);
            response.setStatus(HttpServletResponse.SC_CREATED);
            response.setContentType("text/plain;charset=UTF-8");
            response.getWriter().write("Saved");
        } catch (SQLException error) {
            getServletContext().log("Could not save NOVA conversation entry", error);
            response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR, "History database is unavailable.");
        }
    }
}
