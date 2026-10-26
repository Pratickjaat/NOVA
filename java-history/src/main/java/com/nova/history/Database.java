package com.nova.history;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

/** JDBC connection settings are provided through environment variables. */
public final class Database {
    private Database() {}

    public static Connection getConnection() throws SQLException {
        String url = setting("NOVA_DB_URL", "jdbc:mysql://localhost:3306/nova_history?serverTimezone=UTC");
        String user = setting("NOVA_DB_USER", "root");
        String password = setting("NOVA_DB_PASSWORD", "");
        try {
            // Explicit loading ensures the connector is visible from Tomcat's webapp classloader.
            Class.forName("com.mysql.cj.jdbc.Driver");
        } catch (ClassNotFoundException error) {
            throw new SQLException("MySQL Connector/J is missing from the web application", error);
        }
        return DriverManager.getConnection(url, user, password);
    }

    private static String setting(String key, String fallback) {
        String value = System.getenv(key);
        return value == null || value.isBlank() ? fallback : value;
    }
}
