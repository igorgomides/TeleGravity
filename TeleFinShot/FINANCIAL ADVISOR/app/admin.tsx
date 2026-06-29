import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, ScrollView, FlatList, Alert, RefreshControl } from 'react-native';
import { Text, Surface, Divider, IconButton, Avatar, Button, ActivityIndicator, Snackbar } from 'react-native-paper';
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
    warning: '#FFA726',
};

type UserProfile = {
    id: string;
    email: string;
    full_name: string | null;
    avatar_url: string | null;
    created_at: string;
    updated_at: string;
};

export default function AdminDashboardScreen() {
    const router = useRouter();
    const [users, setUsers] = useState<UserProfile[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [snackbarVisible, setSnackbarVisible] = useState(false);
    const [snackbarMessage, setSnackbarMessage] = useState('');
    const [sendingResetFor, setSendingResetFor] = useState<string | null>(null);

    const fetchUsers = useCallback(async () => {
        try {
            const { data, error } = await supabase.rpc('get_all_users');
            if (error) {
                // Fallback: try querying profiles directly (works if admin has access)
                const { data: profileData, error: profileError } = await supabase
                    .from('profiles')
                    .select('id, email, full_name, avatar_url, created_at, updated_at')
                    .order('created_at', { ascending: false });

                if (profileError) {
                    console.error('Failed to fetch users:', profileError);
                    showSnackbar('Erro ao carregar usuários. Verifique a função SQL.');
                    return;
                }
                setUsers(profileData || []);
            } else {
                setUsers(data || []);
            }
        } catch (e) {
            console.error('Failed to fetch users:', e);
            showSnackbar('Erro de conexão ao carregar usuários.');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    const onRefresh = useCallback(() => {
        setRefreshing(true);
        fetchUsers();
    }, [fetchUsers]);

    const showSnackbar = (message: string) => {
        setSnackbarMessage(message);
        setSnackbarVisible(true);
    };

    const handlePasswordReset = async (email: string) => {
        Alert.alert(
            'Confirmar Reset de Senha',
            `Deseja enviar um link de redefinição de senha para:\n\n${email}?`,
            [
                { text: 'Cancelar', style: 'cancel' },
                {
                    text: 'Enviar Link',
                    onPress: async () => {
                        setSendingResetFor(email);
                        try {
                            const { error } = await supabase.auth.resetPasswordForEmail(email);
                            if (error) {
                                showSnackbar(`Erro: ${error.message}`);
                            } else {
                                showSnackbar(`✅ Link de reset enviado para ${email}`);
                            }
                        } catch (e) {
                            showSnackbar('Erro ao enviar link de reset.');
                        } finally {
                            setSendingResetFor(null);
                        }
                    },
                },
            ]
        );
    };

    const formatDate = (dateString: string) => {
        const d = new Date(dateString);
        return `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getFullYear()}`;
    };

    const renderUserCard = ({ item }: { item: UserProfile }) => (
        <Surface style={styles.userCard} elevation={1}>
            <View style={styles.userCardRow}>
                <View style={styles.userCardLeft}>
                    {item.avatar_url ? (
                        <Avatar.Image size={48} source={{ uri: item.avatar_url }} />
                    ) : (
                        <Avatar.Text
                            size={48}
                            label={item.full_name ? item.full_name.charAt(0).toUpperCase() : item.email.charAt(0).toUpperCase()}
                            style={{ backgroundColor: PALETTE.accentBlack }}
                            color="#FFF"
                        />
                    )}
                    <View style={styles.userInfo}>
                        <Text variant="titleSmall" style={styles.userName} numberOfLines={1}>
                            {item.full_name || 'Sem nome definido'}
                        </Text>
                        <Text variant="bodySmall" style={styles.userEmail} numberOfLines={1}>
                            {item.email}
                        </Text>
                        <Text variant="labelSmall" style={styles.userDate}>
                            Cadastro: {formatDate(item.created_at)}
                        </Text>
                    </View>
                </View>

                <View style={styles.userCardActions}>
                    {sendingResetFor === item.email ? (
                        <ActivityIndicator size={20} color={PALETTE.warning} />
                    ) : (
                        <IconButton
                            icon="lock-reset"
                            size={22}
                            iconColor={PALETTE.warning}
                            onPress={() => handlePasswordReset(item.email)}
                            style={styles.resetButton}
                        />
                    )}
                </View>
            </View>
        </Surface>
    );

    return (
        <View style={styles.container}>
            <View style={styles.header}>
                <IconButton
                    icon="arrow-left"
                    iconColor={PALETTE.textPrimary}
                    size={28}
                    onPress={() => router.back()}
                    style={{ marginLeft: -12 }}
                />
                <Text variant="headlineMedium" style={styles.headerTitle}>
                    Admin Command Center
                </Text>
                <Text variant="bodyLarge" style={styles.headerSubtitle}>
                    Gerencie usuários e métricas da plataforma.
                </Text>
            </View>

            {/* Global Stats */}
            <Surface style={styles.statsCard} elevation={2}>
                <View style={styles.statsRow}>
                    <View style={styles.statItem}>
                        <Text variant="headlineLarge" style={styles.statNumber}>
                            {loading ? '...' : users.length}
                        </Text>
                        <Text variant="labelMedium" style={styles.statLabel}>Usuários</Text>
                    </View>
                    <View style={styles.statDivider} />
                    <View style={styles.statItem}>
                        <Text variant="headlineLarge" style={[styles.statNumber, { color: PALETTE.primary }]}>
                            Gemini 2.5
                        </Text>
                        <Text variant="labelMedium" style={styles.statLabel}>AI Engine</Text>
                    </View>
                    <View style={styles.statDivider} />
                    <View style={styles.statItem}>
                        <Text variant="headlineLarge" style={[styles.statNumber, { color: PALETTE.primary }]}>
                            ●
                        </Text>
                        <Text variant="labelMedium" style={styles.statLabel}>Supabase</Text>
                    </View>
                </View>
            </Surface>

            {/* User List */}
            <Text variant="titleMedium" style={styles.sectionTitle}>
                Usuários Cadastrados
            </Text>

            {loading ? (
                <ActivityIndicator color={PALETTE.primary} style={{ marginTop: 32 }} />
            ) : (
                <FlatList
                    data={users}
                    keyExtractor={(item) => item.id}
                    renderItem={renderUserCard}
                    contentContainerStyle={styles.listContent}
                    showsVerticalScrollIndicator={false}
                    refreshControl={
                        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[PALETTE.primary]} />
                    }
                    ListEmptyComponent={
                        <View style={styles.emptyState}>
                            <Text variant="bodyLarge" style={styles.emptyText}>
                                Nenhum usuário cadastrado ainda.
                            </Text>
                        </View>
                    }
                />
            )}

            <Snackbar
                visible={snackbarVisible}
                onDismiss={() => setSnackbarVisible(false)}
                duration={4000}
                style={styles.snackbar}
            >
                {snackbarMessage}
            </Snackbar>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: PALETTE.background,
        padding: 16,
    },
    header: {
        marginTop: 24,
        marginBottom: 16,
    },
    headerTitle: {
        fontWeight: 'bold',
        color: PALETTE.textPrimary,
        marginBottom: 4,
    },
    headerSubtitle: {
        color: PALETTE.textSecondary,
    },
    statsCard: {
        backgroundColor: PALETTE.card,
        padding: 20,
        borderRadius: 24,
        marginBottom: 24,
    },
    statsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-around',
    },
    statItem: {
        alignItems: 'center',
        flex: 1,
    },
    statNumber: {
        fontWeight: 'bold',
        color: PALETTE.textPrimary,
        fontSize: 22,
    },
    statLabel: {
        color: PALETTE.textSecondary,
        marginTop: 4,
    },
    statDivider: {
        width: 1,
        height: 40,
        backgroundColor: '#E8E8E8',
    },
    sectionTitle: {
        fontWeight: 'bold',
        color: PALETTE.accentBlack,
        marginBottom: 12,
    },
    listContent: {
        paddingBottom: 32,
    },
    userCard: {
        backgroundColor: PALETTE.card,
        padding: 16,
        borderRadius: 20,
        marginBottom: 10,
    },
    userCardRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
    },
    userCardLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        flex: 1,
    },
    userInfo: {
        marginLeft: 14,
        flex: 1,
    },
    userName: {
        fontWeight: 'bold',
        color: PALETTE.textPrimary,
    },
    userEmail: {
        color: PALETTE.textSecondary,
        marginTop: 2,
    },
    userDate: {
        color: '#AAAAAA',
        marginTop: 4,
    },
    userCardActions: {
        marginLeft: 8,
    },
    resetButton: {
        backgroundColor: '#FFF3E0',
        borderRadius: 12,
    },
    emptyState: {
        alignItems: 'center',
        marginTop: 40,
    },
    emptyText: {
        color: PALETTE.textSecondary,
    },
    snackbar: {
        backgroundColor: PALETTE.accentBlack,
    },
});
