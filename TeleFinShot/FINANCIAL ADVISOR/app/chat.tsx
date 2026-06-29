import AsyncStorage from '@react-native-async-storage/async-storage';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';
import * as ImagePicker from 'expo-image-picker';
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { FlatList, Image, StyleSheet, View } from 'react-native';
import { ActivityIndicator, IconButton, Menu, Text, TextInput } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { supabase } from '../lib/supabase';
import { useAuth } from '../providers/AuthProvider';
import { processFinancialChat } from '../services/gemini';

const PALETTE = {
    background: '#F4F7F6',
    card: '#FFFFFF',
    primary: '#0CD179',
    textPrimary: '#111111',
    textSecondary: '#666666',
    error: '#FF4D4D',
    accentBlack: '#1A1A1A',
};

type Message = {
    id: string;
    text: string;
    sender: 'ai' | 'user';
};

export default function ChatScreen() {
    const router = useRouter();
    const [inputText, setInputText] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [menuVisible, setMenuVisible] = useState(false);
    const [selectedImage, setSelectedImage] = useState<{ uri: string; base64: string; mimeType: string, isDoc?: boolean, name?: string } | null>(null);
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            text: "Hey! 👋 I'm your Financial Snapshot assistant. To get started, what is your average monthly income? (Include salary, bonuses, or side hustles)",
            sender: 'ai',
        },
    ]);
    const flatListRef = useRef<FlatList>(null);
    const [isRestoring, setIsRestoring] = useState(true);
    const { user } = useAuth();
    const [conversationId, setConversationId] = useState<string | null>(null);
    const insets = useSafeAreaInsets();

    useEffect(() => {
        const loadHistory = async () => {
            try {
                if (user) {
                    // Load from Supabase first
                    const { data, error } = await supabase
                        .from('conversations')
                        .select('id, messages')
                        .eq('user_id', user.id)
                        .eq('is_completed', false)
                        .order('updated_at', { ascending: false })
                        .limit(1)
                        .single();

                    if (data && data.messages.length > 0) {
                        setConversationId(data.id);
                        setMessages(data.messages);
                        return;
                    }
                }

                // Fallback to local storage
                const storedMessages = await AsyncStorage.getItem('@chat_messages');
                if (storedMessages) {
                    setMessages(JSON.parse(storedMessages));
                }
            } catch (e) {
                console.error("Failed to load chat history", e);
            } finally {
                setIsRestoring(false);
            }
        };
        loadHistory();
    }, [user]);

    useEffect(() => {
        if (!isRestoring) {
            AsyncStorage.setItem('@chat_messages', JSON.stringify(messages)).catch(e => console.error("Failed to save chat history", e));

            // Sync to Supabase
            if (user && messages.length > 1) { // Only sync if there's actual discussion
                syncToSupabase(messages);
            }
        }
    }, [messages, isRestoring]);

    const syncToSupabase = async (currentMessages: Message[]) => {
        try {
            if (conversationId) {
                await supabase
                    .from('conversations')
                    .update({ messages: currentMessages, updated_at: new Date().toISOString() })
                    .eq('id', conversationId);
            } else {
                const { data, error } = await supabase
                    .from('conversations')
                    .insert([{ user_id: user?.id, messages: currentMessages, title: 'Financial Interview' }])
                    .select('id')
                    .single();

                if (data) setConversationId(data.id);
            }
        } catch (error) {
            console.error('Supabase sync failed', error);
        }
    };

    const handleRestart = async () => {
        setMenuVisible(false);
        try {
            await AsyncStorage.removeItem('@chat_messages');
            setConversationId(null);
            setMessages([{
                id: '1',
                text: "Hey! 👋 I'm your Financial Snapshot assistant. To get started, what is your average monthly income? (Include salary, bonuses, or side hustles)",
                sender: 'ai',
            }]);

            if (user && conversationId) {
                await supabase.from('conversations').update({ is_completed: true }).eq('id', conversationId);
            }
        } catch (e) { }
    };

    const pickImage = async () => {
        setMenuVisible(false);
        const result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ['images'],
            allowsEditing: true,
            quality: 0.8,
        });

        if (!result.canceled && result.assets[0]) {
            const asset = result.assets[0];
            try {
                const base64 = await FileSystem.readAsStringAsync(asset.uri, { encoding: 'base64' });
                setSelectedImage({
                    uri: asset.uri,
                    base64,
                    mimeType: asset.mimeType || 'image/jpeg',
                });
            } catch (e) {
                console.error("Failed to read image", e);
            }
        }
    };

    const pickDocument = async () => {
        setMenuVisible(false);
        const result = await DocumentPicker.getDocumentAsync({
            type: ['application/pdf', 'text/plain'],
            copyToCacheDirectory: true
        });

        if (!result.canceled && result.assets[0]) {
            const asset = result.assets[0];
            try {
                const base64 = await FileSystem.readAsStringAsync(asset.uri, { encoding: 'base64' });
                setSelectedImage({
                    uri: asset.uri,
                    base64,
                    mimeType: asset.mimeType || 'application/pdf',
                    isDoc: true,
                    name: asset.name
                });
            } catch (e) {
                console.error("Failed to read document", e);
            }
        }
    };

    const handleSend = async () => {
        if (!inputText.trim() && !selectedImage) return;

        let displayMsgText = inputText.trim() || "Uploaded a document.";
        if (selectedImage && inputText.trim()) {
            displayMsgText = `[Attached] ${inputText.trim()}`;
        }

        const userMessage: Message = {
            id: Date.now().toString(),
            text: displayMsgText,
            sender: 'user',
        };

        setMessages((prev) => [...prev, userMessage]);
        const currentInput = inputText;
        const currentImage = selectedImage;

        setInputText('');
        setSelectedImage(null);
        setIsTyping(true);

        const history = messages.map(m => `${m.sender.toUpperCase()}: ${m.text}`).join('\n');

        const aiRes = await processFinancialChat(
            history,
            currentInput || "Extract the financial numbers from this document.",
            currentImage?.base64,
            currentImage?.mimeType
        );

        if (aiRes) {
            const aiReplyMsg: Message = {
                id: (Date.now() + 1).toString(),
                text: aiRes.aiReply || "Okay, got it.",
                sender: 'ai',
            };
            setMessages((prev) => [...prev, aiReplyMsg]);

            if (aiRes.isComplete) {
                // Save the finalized snapshot to local storage so the Welcome page knows we have data
                await AsyncStorage.setItem('completedSnapshot', JSON.stringify(aiRes));

                if (user && conversationId) {
                    await supabase.from('conversations').update({
                        is_completed: true,
                        snapshot_data: aiRes
                    }).eq('id', conversationId);
                }

                setTimeout(() => {
                    router.push({
                        pathname: '/snapshot',
                        params: {
                            personalIncome: aiRes.personalIncome,
                            spouseIncome: aiRes.spouseIncome,
                            otherIncome: aiRes.otherIncome,
                            fixedMonthlyExpenses: aiRes.fixedMonthlyExpenses,
                            mortgageDebt: aiRes.mortgageDebt,
                            mortgageInterestRate: aiRes.mortgageInterestRate,
                            carLoanDebt: aiRes.carLoanDebt,
                            carLoanInterestRate: aiRes.carLoanInterestRate,
                            creditCardDebt: aiRes.creditCardDebt,
                            creditCardInterestRate: aiRes.creditCardInterestRate,
                            creditCardLimit: aiRes.creditCardLimit,
                            lineOfCreditBalance: aiRes.lineOfCreditBalance,
                            lineOfCreditInterestRate: aiRes.lineOfCreditInterestRate,
                            banksUsed: aiRes.banksUsed?.join(', '),
                            hasRRSP: aiRes.hasRRSP?.toString(),
                            hasChildren: aiRes.hasChildren?.toString(),
                            usesChildBenefits: aiRes.usesChildBenefits?.toString(),
                            spendingHabitsSummary: aiRes.spendingHabitsSummary
                        }
                    });
                }, 2000);
            }
        } else {
            setMessages((prev) => [...prev, {
                id: (Date.now() + 1).toString(),
                text: "Sorry, I had trouble processing that. Can you repeat?",
                sender: 'ai',
            }]);
        }

        setIsTyping(false);
    };

    const lastAiIndex = [...messages].reverse().findIndex(m => m.sender === 'ai');
    const actualLastAiIndex = lastAiIndex !== -1 ? messages.length - 1 - lastAiIndex : -1;

    const renderMessage = ({ item, index }: { item: Message, index: number }) => {
        const isAi = item.sender === 'ai';
        const isLatestAi = isAi && index === actualLastAiIndex;

        return (
            <View style={[styles.messageRow, isAi ? styles.messageRowAi : styles.messageRowUser]}>
                <View
                    style={[
                        styles.messageBubble,
                        isAi ? styles.bubbleAi : styles.bubbleUser,
                    ]}
                >
                    <Text style={{
                        color: isAi ? (isLatestAi ? PALETTE.textPrimary : '#999999') : '#FFFFFF',
                        lineHeight: isAi ? (isLatestAi ? 38 : 28) : 24,
                        fontSize: isAi ? (isLatestAi ? 30 : 20) : 16,
                        fontFamily: isAi ? (isLatestAi ? 'Jost_900Black' : 'Jost_500Medium') : 'Jost_500Medium',
                        fontWeight: 'normal',
                        letterSpacing: isAi ? -1 : 0,
                    }}>
                        {item.text}
                    </Text>
                </View>
            </View>
        );
    };

    return (
        <View style={styles.container}>
            <FlatList
                ref={flatListRef}
                data={messages}
                keyExtractor={(item) => item.id}
                renderItem={renderMessage}
                contentContainerStyle={styles.listContent}
                onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
                ListFooterComponent={isTyping ? <View style={{ alignItems: 'flex-start', paddingVertical: 10 }}><ActivityIndicator color={PALETTE.primary} /></View> : null}
            />

            <View style={[styles.inputContainerOuter, { paddingBottom: Math.max(insets.bottom, 16) }]}>
                {selectedImage && (
                    <View style={styles.imagePreviewContainer}>
                        {selectedImage.isDoc ? (
                            <View style={styles.docPreview}>
                                <Text style={{ fontSize: 12, color: PALETTE.textSecondary }} numberOfLines={1}>{selectedImage.name}</Text>
                            </View>
                        ) : (
                            <Image source={{ uri: selectedImage.uri }} style={styles.imagePreview} />
                        )}
                        <IconButton
                            icon="close-circle"
                            size={20}
                            style={styles.imageRemoveBtn}
                            iconColor={PALETTE.error}
                            onPress={() => setSelectedImage(null)}
                        />
                    </View>
                )}
                <View style={styles.inputContainerInner}>
                    <Menu
                        visible={menuVisible}
                        onDismiss={() => setMenuVisible(false)}
                        anchor={
                            <IconButton
                                icon="paperclip"
                                size={24}
                                iconColor={PALETTE.textSecondary}
                                onPress={() => setMenuVisible(true)}
                            />
                        }
                    >
                        <Menu.Item onPress={pickImage} title="Attach Image" leadingIcon="image" />
                        <Menu.Item onPress={pickDocument} title="Attach Document" leadingIcon="file-document" />
                        <Menu.Item onPress={handleRestart} title="Restart Interview" leadingIcon="refresh" />
                    </Menu>

                    <TextInput
                        mode="flat"
                        placeholder={selectedImage ? "Add a message..." : "Type your answer..."}
                        value={inputText}
                        onChangeText={setInputText}
                        style={styles.textInput}
                        underlineColor="transparent"
                        activeUnderlineColor="transparent"
                        placeholderTextColor={PALETTE.textSecondary}
                        onSubmitEditing={handleSend}
                    />

                    <IconButton
                        icon="arrow-up-circle"
                        size={32}
                        iconColor={inputText.trim() || selectedImage ? PALETTE.primary : '#E0E0E0'}
                        onPress={handleSend}
                    />
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#FFFFFF',
    },
    listContent: {
        padding: 24,
        paddingTop: 48,
        flexGrow: 1,
        justifyContent: 'flex-end',
    },
    messageRow: {
        flexDirection: 'row',
        marginBottom: 32,
        width: '100%',
    },
    messageRowAi: {
        justifyContent: 'flex-start',
    },
    messageRowUser: {
        justifyContent: 'flex-end',
    },
    messageBubble: {
        maxWidth: '90%',
        padding: 16,
        borderRadius: 24,
    },
    bubbleAi: {
        backgroundColor: 'transparent',
        paddingHorizontal: 0,
        paddingVertical: 0,
        maxWidth: '100%',
    },
    bubbleUser: {
        backgroundColor: PALETTE.accentBlack,
        paddingHorizontal: 20,
        paddingVertical: 14,
        borderBottomRightRadius: 4,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.1,
        shadowRadius: 10,
        elevation: 1,
    },
    inputContainerOuter: {
        backgroundColor: '#FFFFFF',
        padding: 16,
        paddingTop: 12,
        borderTopWidth: 1,
        borderTopColor: 'rgba(0,0,0,0.05)',
    },
    inputContainerInner: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#F5F5F5',
        borderRadius: 32,
        paddingHorizontal: 8,
        paddingVertical: 4,
    },
    imagePreviewContainer: {
        marginBottom: 12,
        alignSelf: 'flex-start',
        position: 'relative'
    },
    imagePreview: {
        width: 64,
        height: 64,
        borderRadius: 16,
    },
    docPreview: {
        width: 100,
        height: 64,
        borderRadius: 16,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 8,
        backgroundColor: '#E8E8E8'
    },
    imageRemoveBtn: {
        position: 'absolute',
        top: -16,
        right: -16,
        backgroundColor: PALETTE.card,
        margin: 0
    },
    textInput: {
        flex: 1,
        backgroundColor: 'transparent',
        height: 50,
        fontSize: 16,
        color: PALETTE.textPrimary,
    }
});
