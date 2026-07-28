import 'package:path/path.dart' as path;
import 'package:sqflite/sqflite.dart';

import 'models.dart';

class LocalLogStore {
  Database? _database;

  Future<Database> get _db async {
    final existing = _database;
    if (existing != null) return existing;
    final databasePath = await getDatabasesPath();
    final db = await openDatabase(
      path.join(databasePath, 'access_mobile_log.db'),
      version: 1,
      onCreate: (database, _) async {
        await database.execute('''
          CREATE TABLE checkin_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_token TEXT,
            folio_turno TEXT,
            created_at TEXT NOT NULL,
            recepcionista_login TEXT NOT NULL
          )
        ''');
      },
    );
    _database = db;
    return db;
  }

  Future<void> add({
    required String? qrToken,
    required String? folioTurno,
    required String recepcionistaLogin,
  }) async {
    final db = await _db;
    await db.insert('checkin_log', {
      'qr_token': qrToken,
      'folio_turno': folioTurno,
      'created_at': DateTime.now().toUtc().toIso8601String(),
      'recepcionista_login': recepcionistaLogin,
    });
  }

  Future<List<ActivityLogEntry>> latest() async {
    final db = await _db;
    final rows = await db.query('checkin_log', orderBy: 'created_at DESC', limit: 200);
    return rows.map(ActivityLogEntry.fromMap).toList();
  }
}
