import AsyncStorage from '@react-native-async-storage/async-storage';
import { decode } from 'base64-arraybuffer';
import * as FileSystem from 'expo-file-system';
import * as ImagePicker from 'expo-image-picker';
import { useFocusEffect, useRouter } from 'expo-router';
import React, { useCallback, useState } from 'react';
import { Alert, Image, StyleSheet, View } from 'react-native';
import { Avatar, Button, IconButton, Text, TextInput } from 'react-native-paper';
import { supabase } from '../lib/supabase';
import { useAuth } from '../providers/AuthProvider';

const PALETTE = {
    background: '#F4F7F6',
    card: '#FFFFFF',
    primary: '#0CD179',
    textPrimary: '#111111',
    textSecondary: '#666666',
    error: '#FF4D4D',
    accentBlack: '#1A1A1A',
};

export default function WelcomeScreen() {
    const router = useRouter();
    const { session, user } = useAuth();
    const [snapshotParams, setSnapshotParams] = useState<any>(null);
    const [profile, setProfile] = useState<{ full_name: string; avatar_url: string } | null>(null);
    const [isEditing, setIsEditing] = useState(false);
    const [editName, setEditName] = useState('');
    const [loadingProfile, setLoadingProfile] = useState(false);

    useFocusEffect(
        useCallback(() => {
            const checkExistingSnapshot = async () => {
                const stored = await AsyncStorage.getItem('completedSnapshot');
                if (stored) {
                    const aiRes = JSON.parse(stored);
                    setSnapshotParams({ ...aiRes });
                } else {
                    setSnapshotParams(null);
                }
            };
            checkExistingSnapshot();
        }, [])
    );

    React.useEffect(() => {
        if (user) {
            fetchProfile();
        }
    }, [user]);

    const fetchProfile = async () => {
        try {
            if (!user) return;
            const { data, error } = await supabase
                .from('profiles')
                .select('full_name, avatar_url')
                .eq('id', user.id)
                .single();

            if (error) throw error;
            setProfile(data);
            setEditName(data?.full_name || '');
        } catch (error) {
            console.error('Error loading profile:', error);
        }
    };

    const handleSaveProfile = async () => {
        try {
            setLoadingProfile(true);
            const { error } = await supabase
                .from('profiles')
                .update({ full_name: editName })
                .eq('id', user?.id);

            if (error) throw error;
            setProfile(prev => ({ ...prev, full_name: editName } as any));
            setIsEditing(false);
        } catch (error) {
            console.error('Failed to update profile');
        } finally {
            setLoadingProfile(false);
        }
    };

    const handlePickAvatar = async () => {
        try {
            const result = await ImagePicker.launchImageLibraryAsync({
                mediaTypes: ['images'],
                allowsEditing: true,
                aspect: [1, 1],
                quality: 0.5,
            });

            if (!result.canceled && result.assets[0]) {
                Alert.alert('Debug', `Image selected: ${result.assets[0].uri.substring(0, 50)}...`);
                await uploadAvatar(result.assets[0].uri);
            } else {
                Alert.alert('Debug', 'Image picker was cancelled');
            }
        } catch (error: any) {
            Alert.alert('Erro ao selecionar foto', error?.message || 'Unknown error');
        }
    };

    const uploadAvatar = async (uri: string) => {
        try {
            setLoadingProfile(true);

            // Step 1: Read file as base64
            const base64 = await FileSystem.readAsStringAsync(uri, {
                encoding: 'base64',
            });
            Alert.alert('Step 1 OK', `Base64 length: ${base64.length}`);

            const ext = uri.split('.').pop()?.toLowerCase() || 'jpg';
            const fileName = `${user?.id}/${Date.now()}.${ext}`;
            const contentType = ext === 'png' ? 'image/png' : 'image/jpeg';

            // Step 2: Upload to Supabase Storage
            const { error: uploadError } = await supabase.storage
                .from('avatars')
                .upload(fileName, decode(base64), {
                    contentType,
                    upsert: true,
                });

            if (uploadError) {
                Alert.alert('Step 2 FALHOU', `Upload error: ${uploadError.message}`);
                throw uploadError;
            }
            Alert.alert('Step 2 OK', `Uploaded: ${fileName}`);

            // Step 3: Get public URL
            const { data: { publicUrl } } = supabase.storage
                .from('avatars')
                .getPublicUrl(fileName);

            // Step 4: Update profile
            const { error: updateError } = await supabase
                .from('profiles')
                .update({ avatar_url: publicUrl })
                .eq('id', user?.id);

            if (updateError) {
                Alert.alert('Step 4 FALHOU', `Profile update: ${updateError.message}`);
                throw updateError;
            }

            setProfile(prev => ({ ...prev, avatar_url: publicUrl } as any));
            Alert.alert('Sucesso!', 'Avatar atualizado com sucesso!');

        } catch (error: any) {
            Alert.alert('ERRO no Upload', error?.message || JSON.stringify(error));
        } finally {
            setLoadingProfile(false);
        }
    };

    const handleSignOut = async () => {
        await supabase.auth.signOut();
    };

    return (
        <View style={styles.container}>
            <View style={styles.content}>
                <Image
                    source={require('../assets/images/logo.png')}
                    style={styles.logo}
                    resizeMode="contain"
                />
                <Text variant="displaySmall" style={styles.title}>
                    Financial Snapshot
                </Text>
                <Text variant="bodyLarge" style={styles.subtitle}>
                    Stop worrying if you are making the most of your money. Get a clear overview of your financial health without the complex numbers or overwhelm.
                </Text>

                {session && user ? (
                    <View style={styles.profileContainer}>
                        {/* PROFILE EDIT SECTION */}
                        <View style={styles.avatarWrapper}>
                            {profile?.avatar_url ? (
                                <Avatar.Image size={64} source={{ uri: profile.avatar_url }} style={styles.avatar} />
                            ) : (
                                <Avatar.Text
                                    size={64}
                                    label={profile?.full_name ? profile.full_name.charAt(0).toUpperCase() : user.email?.charAt(0).toUpperCase() || 'U'}
                                    style={styles.avatar}
                                    color="#FFF"
                                />
                            )}
                            <View style={styles.editBadge}>
                                <IconButton icon="camera" size={12} iconColor="#FFF" style={{ margin: 0 }} onPress={handlePickAvatar} disabled={loadingProfile} />
                            </View>
                        </View>

                        {isEditing ? (
                            <View style={styles.nameEditRow}>
                                <TextInput
                                    value={editName}
                                    onChangeText={setEditName}
                                    mode="outlined"
                                    dense
                                    placeholder="Your Full Name"
                                    style={{ flex: 1, backgroundColor: '#FFF' }}
                                    activeOutlineColor={PALETTE.primary}
                                />
                                <IconButton
                                    icon={loadingProfile ? "loading" : "check"}
                                    mode="contained"
                                    containerColor={PALETTE.primary}
                                    iconColor="#FFF"
                                    size={20}
                                    onPress={handleSaveProfile}
                                />
                            </View>
                        ) : (
                            <View style={styles.nameDisplayRow}>
                                <View>
                                    <Text style={styles.userName}>{profile?.full_name || 'Set your name'}</Text>
                                    <Text style={styles.userEmail}>{user.email}</Text>
                                </View>
                                <IconButton icon="pencil-outline" size={20} onPress={() => setIsEditing(true)} />
                            </View>
                        )}
                        {/* END PROFILE EDIT SECTION */}

                        {process.env.EXPO_PUBLIC_ADMIN_EMAILS?.split(',').map((e: string) => e.trim()).includes(user.email || '') && (
                            <Button
                                mode="contained"
                                icon="shield-account"
                                onPress={() => router.push('/admin')}
                                style={[styles.button, { marginTop: 12, backgroundColor: PALETTE.error }]}
                                contentStyle={styles.buttonContent}
                                textColor="#FFF"
                            >
                                Admin Dashboard
                            </Button>
                        )}

                        {snapshotParams ? (
                            <View style={{ width: '100%', marginTop: 24 }}>
                                <Button
                                    mode="contained"
                                    onPress={() => router.push({ pathname: '/snapshot', params: snapshotParams })}
                                    style={[styles.button, { backgroundColor: PALETTE.primary }]}
                                    contentStyle={styles.buttonContent}
                                    textColor="#FFF"
                                >
                                    View My Snapshot
                                </Button>
                                <Button
                                    mode="contained"
                                    onPress={() => router.push({ pathname: '/upsell', params: snapshotParams })}
                                    style={[styles.button, { marginTop: 12, backgroundColor: PALETTE.accentBlack }]}
                                    contentStyle={styles.buttonContent}
                                    textColor="#FFF"
                                >
                                    Explore Pro Plan
                                </Button>
                                <Button
                                    mode="outlined"
                                    onPress={() => router.push('/chat')}
                                    style={[styles.button, { marginTop: 12, borderColor: PALETTE.textSecondary }]}
                                    contentStyle={styles.buttonContent}
                                    textColor={PALETTE.textPrimary}
                                >
                                    Start a New Interview
                                </Button>
                            </View>
                        ) : (
                            <Button
                                mode="contained"
                                onPress={() => router.push('/chat')}
                                style={[styles.button, { marginTop: 24, backgroundColor: PALETTE.primary }]}
                                contentStyle={styles.buttonContent}
                                textColor="#FFF"
                            >
                                Start Financial Interview
                            </Button>
                        )}

                        <Button
                            mode="text"
                            onPress={handleSignOut}
                            style={{ marginTop: 16 }}
                            textColor={PALETTE.textSecondary}
                        >
                            Sign Out
                        </Button>
                    </View>
                ) : (
                    <View style={styles.guestContainer}>
                        <Button
                            mode="contained"
                            onPress={() => router.push('/login')}
                            style={[styles.button, { backgroundColor: PALETTE.primary }]}
                            contentStyle={styles.buttonContent}
                            textColor="#FFF"
                        >
                            Log In
                        </Button>
                        <Button
                            mode="outlined"
                            onPress={() => router.push('/signup')}
                            style={[styles.button, { marginTop: 12, borderColor: PALETTE.textSecondary }]}
                            contentStyle={styles.buttonContent}
                            textColor={PALETTE.textPrimary}
                        >
                            Create an Account
                        </Button>
                    </View>
                )}
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: PALETTE.background
    },
    content: {
        flex: 1,
        padding: 24,
        justifyContent: 'center',
        alignItems: 'center',
    },
    title: {
        fontFamily: 'Jost_700Bold',
        fontWeight: 'normal',
        marginBottom: 16,
        textAlign: 'center',
        color: PALETTE.primary
    },
    logo: {
        width: 120,
        height: 120,
        marginBottom: 16,
    },
    subtitle: {
        textAlign: 'center',
        marginBottom: 48,
        lineHeight: 24,
        color: PALETTE.textSecondary
    },
    profileContainer: {
        width: '100%',
        alignItems: 'center',
        backgroundColor: PALETTE.card,
        padding: 24,
        borderRadius: 24,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 10 },
        shadowOpacity: 0.04,
        shadowRadius: 20,
        elevation: 2,
    },
    avatarWrapper: {
        position: 'relative',
        marginBottom: 16,
    },
    avatar: {
        backgroundColor: PALETTE.primary,
    },
    editBadge: {
        position: 'absolute',
        bottom: 0,
        right: 0,
        backgroundColor: PALETTE.accentBlack,
        borderRadius: 14,
        width: 28,
        height: 28,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 2,
        borderColor: '#FFF',
    },
    nameDisplayRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
        paddingHorizontal: 8,
        marginBottom: 16,
    },
    nameEditRow: {
        flexDirection: 'row',
        alignItems: 'center',
        width: '100%',
        gap: 8,
        marginBottom: 16,
    },
    userName: {
        fontSize: 18,
        fontFamily: 'Jost_700Bold',
        fontWeight: 'normal',
        color: PALETTE.textPrimary,
        textAlign: 'center',
    },
    userEmail: {
        fontSize: 14,
        color: PALETTE.textSecondary,
        textAlign: 'center',
    },
    guestContainer: {
        width: '100%',
        alignItems: 'center',
    },
    button: {
        width: '100%',
        maxWidth: 400,
        borderRadius: 24,
    },
    buttonContent: {
        paddingVertical: 8,
    }
});
