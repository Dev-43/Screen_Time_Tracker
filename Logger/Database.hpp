#pragma once

extern "C" {
#include "sqlite3.h"
}

#include "Shared.hpp"

#include <filesystem>
#include <iostream>
#include <string>

class Database {
private:
    sqlite3* db = nullptr;
    std::string dbPath;

public:
    explicit Database(const std::string& dbName) : dbPath(dbName) {
        std::filesystem::path p(dbName);
        if (p.has_parent_path()) {
            std::error_code ec;
            std::filesystem::create_directories(p.parent_path(), ec);
            if (ec) {
                std::cerr << "Warning: could not create DB directory: " << ec.message() << std::endl;
            }
        }

        if (sqlite3_open(dbName.c_str(), &db) != SQLITE_OK) {
            std::cerr << "Cannot open database: " << sqlite3_errmsg(db) << std::endl;
            if (db) {
                sqlite3_close(db);
                db = nullptr;
            }
            return;
        }

        std::cout << "Connected to SQLite database: " << dbName << "\n";
        sqlite3_busy_timeout(db, 3000);

        enableWAL();
        createTable();
    }

    ~Database() {
        if (db) {
            sqlite3_close(db);
            db = nullptr;
        }
    }

    bool isOpen() const {
        return db != nullptr;
    }

    void enableWAL() {
        if (!db) return;

        char* err = nullptr;
        sqlite3_exec(db, "PRAGMA journal_mode=WAL;", nullptr, nullptr, &err);
        if (err) {
            std::cerr << "WAL warning: " << err << std::endl;
            sqlite3_free(err);
        }
    }

    void createTable() {
        if (!db) return;

        const char* sql =
            "CREATE TABLE IF NOT EXISTS screen_logs ("
            "  id             INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  pid            INTEGER,"
            "  app_name       TEXT,"
            "  active_window  TEXT,"
            "  is_idle        INTEGER DEFAULT 0,"
            "  cpu_usage      REAL    DEFAULT 0,"
            "  ram_kb         INTEGER DEFAULT 0,"
            "  timestamp      INTEGER"
            ");"

            "CREATE TABLE IF NOT EXISTS daily_summaries ("
            "  id               INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  date             TEXT    NOT NULL,"
            "  app_name         TEXT    NOT NULL,"
            "  category         TEXT    NOT NULL DEFAULT 'Other',"
            "  total_active_sec INTEGER NOT NULL DEFAULT 0"
            ");"

            "CREATE TABLE IF NOT EXISTS time_limits ("
            "  app_name        TEXT    PRIMARY KEY,"
            "  daily_limit_min INTEGER NOT NULL"
            ");"

            "CREATE TABLE IF NOT EXISTS app_categories ("
            "  app_name TEXT PRIMARY KEY,"
            "  category TEXT NOT NULL DEFAULT 'Other'"
            ");"

            "CREATE INDEX IF NOT EXISTS idx_screen_ts ON screen_logs(timestamp);"
            "CREATE INDEX IF NOT EXISTS idx_screen_app ON screen_logs(app_name);"
            "CREATE INDEX IF NOT EXISTS idx_summary_date ON daily_summaries(date, app_name);";

        char* errMsg = nullptr;
        if (sqlite3_exec(db, sql, nullptr, nullptr, &errMsg) != SQLITE_OK) {
            std::cerr << "Table creation error: " << errMsg << std::endl;
            sqlite3_free(errMsg);
        } else {
            std::cout << "Database schema ready.\n";
        }
    }

    void insertLog(const ScreenLog& log) {
        if (!db) return;

        const char* sql =
            "INSERT INTO screen_logs "
            "(pid, app_name, active_window, is_idle, cpu_usage, ram_kb, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?);";

        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
            std::cerr << "Prepare failed: " << sqlite3_errmsg(db) << std::endl;
            return;
        }

        sqlite3_bind_int(stmt, 1, log.pid);
        sqlite3_bind_text(stmt, 2, log.app_name.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 3, log.active_window.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int(stmt, 4, log.is_idle);
        sqlite3_bind_double(stmt, 5, log.cpu_usage);
        sqlite3_bind_int64(stmt, 6, log.ram_kb);
        sqlite3_bind_int64(stmt, 7, log.timestamp);

        if (sqlite3_step(stmt) != SQLITE_DONE) {
            std::cerr << "Insert failed: " << sqlite3_errmsg(db) << std::endl;
        }

        sqlite3_finalize(stmt);
    }
};
