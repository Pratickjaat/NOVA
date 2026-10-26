package com.nova.history;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;

public class ConversationRepository {
    public record Entry(long id, String speaker, String message, Timestamp createdAt) {}

    public void initialize() throws SQLException {
        String sql = "CREATE TABLE IF NOT EXISTS conversation_history ("
                + "id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
                + "speaker VARCHAR(20) NOT NULL, message TEXT NOT NULL, "
                + "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)";
        try (Connection connection = Database.getConnection(); Statement statement = connection.createStatement()) {
            statement.executeUpdate(sql);
        }
    }

    public void save(String speaker, String message) throws SQLException {
        String sql = "INSERT INTO conversation_history (speaker, message) VALUES (?, ?)";
        try (Connection connection = Database.getConnection(); PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, speaker);
            statement.setString(2, message);
            statement.executeUpdate();
        }
    }

    public List<Entry> latest(int limit) throws SQLException {
        String sql = "SELECT id, speaker, message, created_at FROM conversation_history ORDER BY id DESC LIMIT ?";
        List<Entry> entries = new ArrayList<>();
        try (Connection connection = Database.getConnection(); PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setInt(1, limit);
            try (ResultSet rows = statement.executeQuery()) {
                while (rows.next()) entries.add(new Entry(rows.getLong("id"), rows.getString("speaker"),
                        rows.getString("message"), rows.getTimestamp("created_at")));
            }
        }
        return entries;
    }
}
