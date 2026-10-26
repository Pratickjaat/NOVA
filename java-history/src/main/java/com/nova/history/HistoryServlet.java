package com.nova.history;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.sql.SQLException;

@WebServlet("/history")
public class HistoryServlet extends HttpServlet {
    private final ConversationRepository repository = new ConversationRepository();

    @Override public void init() throws ServletException {
        try { repository.initialize(); }
        catch (SQLException error) { throw new ServletException("Cannot initialize NOVA history database", error); }
    }

    @Override protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
        try {
            request.setAttribute("entries", repository.latest(200));
            request.getRequestDispatcher("/WEB-INF/history.jsp").forward(request, response);
        } catch (SQLException error) {
            throw new ServletException("Cannot load conversation history", error);
        }
    }
}
