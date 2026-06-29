import React, { useState } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform, Alert } from 'react-native';
import { Button, TextInput, Text } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { supabase } from '../lib/supabase';

const PALETTE = {
    background: '#F4F7F6',
    card: '#FFFFFF',
    primary: '#0CD179',
    textPrimary: '#111111',
    textSecondary: '#666666',
    error: '#FF4D4D',
    accentBlack: '#1A1A1A',
};

export default function SignupScreen() {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);

    async function signUpWithEmail() {
        setLoading(true);
        const { error } = await supabase.auth.signUp({
            email,
            password,
        });

        if (error) {
            Alert.alert('Signup failed', error.message);
        } else {
            Alert.alert('Success', 'Please check your email to verify your account!', [
                { text: 'OK', onPress: () => router.replace('/login') }
            ]);
        }
        setLoading(false);
    }

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
            <View style={styles.card}>
                <Text style={styles.header}>Create Account</Text>
                <Text style={styles.subtitle}>Start mastering your finances today.</Text>

                <TextInput
                    label="Email"
                    value={email}
                    onChangeText={setEmail}
                    autoCapitalize="none"
                    keyboardType="email-address"
                    mode="outlined"
                    outlineColor={PALETTE.textSecondary}
                    activeOutlineColor={PALETTE.primary}
                    style={styles.input}
                    theme={{ colors: { background: PALETTE.card } }}
                />
                <TextInput
                    label="Password"
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry
                    mode="outlined"
                    outlineColor={PALETTE.textSecondary}
                    activeOutlineColor={PALETTE.primary}
                    style={styles.input}
                    theme={{ colors: { background: PALETTE.card } }}
                />

                <Button
                    mode="contained"
                    onPress={signUpWithEmail}
                    loading={loading}
                    disabled={loading}
                    style={styles.button}
                    buttonColor={PALETTE.primary}
                    textColor="#FFF"
                >
                    Sign Up
                </Button>

                <View style={styles.footer}>
                    <Text style={{ color: PALETTE.textSecondary }}>Already have an account? </Text>
                    <Text
                        style={styles.link}
                        onPress={() => router.push('/login')}
                    >
                        Log in
                    </Text>
                </View>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: PALETTE.background,
        justifyContent: 'center',
        padding: 16,
    },
    card: {
        backgroundColor: PALETTE.card,
        padding: 24,
        borderRadius: 32,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 10 },
        shadowOpacity: 0.04,
        shadowRadius: 20,
        elevation: 2,
    },
    header: {
        fontSize: 28,
        fontWeight: 'bold',
        color: PALETTE.textPrimary,
        marginBottom: 8,
        textAlign: 'center',
    },
    subtitle: {
        fontSize: 16,
        color: PALETTE.textSecondary,
        marginBottom: 24,
        textAlign: 'center',
    },
    input: {
        marginBottom: 16,
    },
    button: {
        borderRadius: 24,
        paddingVertical: 6,
        marginTop: 8,
    },
    footer: {
        flexDirection: 'row',
        justifyContent: 'center',
        marginTop: 24,
    },
    link: {
        color: PALETTE.primary,
        fontWeight: 'bold',
    },
});
