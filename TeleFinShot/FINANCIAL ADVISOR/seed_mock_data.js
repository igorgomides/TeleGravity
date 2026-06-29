const fs = require('fs');
const path = require('path');

const chatData = JSON.parse(fs.readFileSync(path.join(__dirname, 'extracted_chat.json'), 'utf8'));

const messages = chatData.map((msg, index) => ({
    id: (Date.now() + index).toString(),
    text: msg.text,
    sender: msg.sender
}));

const messagesJsonb = JSON.stringify(messages).replace(/'/g, "''");

const sql = `
-- COPY AND PASTE THIS ENTIRE SCRIPT INTO YOUR SUPABASE SQL EDITOR

DO $$
DECLARE
    target_user_id uuid;
    target_user_email text;
BEGIN
    -- 1. Grab the ID and email of the first user directly from the authentication table
    SELECT id, email INTO target_user_id, target_user_email FROM auth.users LIMIT 1;

    -- If no user exists, throw an error
    IF target_user_id IS NULL THEN
        RAISE EXCEPTION 'Nenhuma conta de usuário encontrada! Crie uma conta no aplicativo primeiro.';
    END IF;

    -- 2. Fix legacy users: Insert into profiles if they don't exist yet
    INSERT INTO public.profiles (id, email)
    VALUES (target_user_id, target_user_email)
    ON CONFLICT (id) DO NOTHING;

    -- 3. Insert the recovered conversation!
    INSERT INTO public.conversations (user_id, messages, title, is_completed)
    VALUES (
        target_user_id,
        '${messagesJsonb}'::jsonb,
        'Old Restored Interview',
        true
    );
END $$;
`;

fs.writeFileSync(path.join(__dirname, 'mock_restore.sql'), sql.trim());
console.log("mock_restore_fixed_v2.sql generated!");
