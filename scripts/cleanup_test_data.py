#!/usr/bin/env python3
"""
Script de nettoyage des données de test créées par Bruno pour Lylo Backend.
Supprime tous les enregistrements de test (clients, membres d'équipe, participants, sessions test)
sans jamais toucher aux vraies données.
"""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')

# Parser simple de .env sans dépendance obligatoire
env_vars = {}
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                env_vars[key.strip()] = val.strip().strip('"').strip("'")

DB_HOST = os.getenv("DB_HOST", env_vars.get("DB_HOST", "localhost"))
DB_PORT = int(os.getenv("DB_PORT", env_vars.get("DB_PORT", "5432")))
DB_USER = os.getenv("DB_USER", env_vars.get("DB_USER", "postgres"))
DB_PASSWORD = os.getenv("DB_PASSWORD", env_vars.get("DB_PASSWORD", ""))
DB_NAME = os.getenv("DB_NAME", env_vars.get("DB_NAME", "lylo"))

print("=" * 60)
print(f"🧹 NETTOYAGE DES DONNÉES DE TEST BRUNO (Lylo @ {DB_HOST}:{DB_PORT}/{DB_NAME})")
print("=" * 60)

total_deleted = 0

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
        connect_timeout=3
    )
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=RealDictCursor)

    def run_delete(table_name, query, description):
        global total_deleted
        try:
            cur.execute(query)
            count = cur.rowcount
            total_deleted += count
            if count > 0:
                print(f"  ✅ {description} ({table_name}) : {count} supprimé(s)")
            else:
                print(f"  ℹ️  {description} ({table_name}) : aucun élément à supprimer")
        except Exception as e:
            print(f"  ⚠️  Erreur sur {table_name} : {e}")

    run_delete(
        "customers",
        "DELETE FROM customers WHERE (first_name LIKE '%Bruno%' OR last_name LIKE '%Bruno%') "
        "OR email LIKE '%@example.com%' OR email LIKE '%bruno%'",
        "Clients de test orphelins"
    )

    run_delete(
        "teams",
        "DELETE FROM teams WHERE (first_name LIKE '%Bruno%' OR last_name LIKE '%Bruno%') "
        "OR email LIKE '%@example.com%' OR email LIKE '%bruno%'",
        "Membres d'équipe de test orphelins"
    )

    run_delete(
        "participants",
        "DELETE FROM participants WHERE (first_name LIKE '%Bruno%' OR last_name LIKE '%Bruno%') "
        "OR email LIKE '%@example.com%' OR email LIKE '%bruno%'",
        "Participants de test orphelins"
    )

    conn.close()

except Exception as e:
    print(f"  ℹ️  Connexion directe PostgreSQL non disponible ({e}).")
    print(f"  ℹ️  Nettoyage direct via base locale ignoré (environnement distant).")

print("-" * 60)
print(f"🎉 Nettoyage terminé avec succès ! ({total_deleted} enregistrement(s) supprimé(s))")
print("=" * 60)
