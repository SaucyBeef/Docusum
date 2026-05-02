INSERT INTO users (email, password_hash, name)
VALUES ('demo@docusum.local', 'demo_hash_not_for_production', 'Demo User')
ON CONFLICT (email) DO NOTHING;
