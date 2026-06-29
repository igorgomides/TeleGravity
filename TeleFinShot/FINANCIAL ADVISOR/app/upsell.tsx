import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, Surface, Button, List } from 'react-native-paper';
import { useRouter } from 'expo-router';

// Custom Palette based on user request (Green, White, Black accents)
const PALETTE = {
    background: '#F4F7F6',
    card: '#FFFFFF',
    primary: '#0CD179',
    textPrimary: '#111111',
    textSecondary: '#666666',
    error: '#FF4D4D',
    accentBlack: '#1A1A1A',
};

export default function UpsellScreen() {
    const router = useRouter();

    return (
        <ScrollView style={styles.container}>
            <View style={styles.header}>
                <Text variant="headlineLarge" style={styles.headerTitle}>
                    Stop Guessing,{'\n'}Start Growing.
                </Text>
                <Text variant="bodyLarge" style={styles.headerSubtitle}>
                    Unlock the Pro Plan and let us do the heavy lifting to find the best Canadian financial products for your lifestyle.
                </Text>
            </View>

            <View style={styles.card}>
                <Text variant="titleMedium" style={styles.cardTitle}>
                    Pro Plan Features
                </Text>
                <View style={styles.listContainer}>
                    <List.Item
                        title="Mortgage Optimization"
                        titleStyle={styles.listItemTitle}
                        description="Find out exactly how much interest you're paying and when to refinance."
                        descriptionStyle={styles.listItemDesc}
                        left={props => <List.Icon {...props} icon="home-analytics" color={PALETTE.primary} />}
                    />
                    <List.Item
                        title="Canadian Tax Benefits (RRSP/TFSA)"
                        titleStyle={styles.listItemTitle}
                        description="Automatic analysis of where to put your money to minimize taxes."
                        descriptionStyle={styles.listItemDesc}
                        left={props => <List.Icon {...props} icon="leaf" color={PALETTE.primary} />}
                    />
                    <List.Item
                        title="Kids Savings Price Matching"
                        titleStyle={styles.listItemTitle}
                        description="Unlock guaranteed government returns for your children's accounts."
                        descriptionStyle={styles.listItemDesc}
                        left={props => <List.Icon {...props} icon="piggy-bank" color={PALETTE.primary} />}
                    />
                    <List.Item
                        title="Credit Card Matching"
                        titleStyle={styles.listItemTitle}
                        description="Stop missing out on travel points and cashback tailored to your exact spending habits."
                        descriptionStyle={styles.listItemDesc}
                        left={props => <List.Icon {...props} icon="credit-card-check" color={PALETTE.primary} />}
                    />
                </View>
            </View>

            <View style={[styles.card, styles.pricingCard]}>
                <Text variant="titleMedium" style={styles.pricingSub}>
                    Start your 14-day Free Trial
                </Text>
                <Text variant="displayMedium" style={styles.pricingTitle}>
                    $9.99<Text style={styles.pricingMonth}>/mo</Text>
                </Text>
                <Button
                    mode="contained"
                    style={styles.subscribeButton}
                    labelStyle={styles.subscribeButtonLabel}
                    onPress={() => alert('Subscription flow would launch here!')}
                >
                    Subscribe Now
                </Button>
                <Button
                    mode="text"
                    style={styles.laterButton}
                    labelStyle={styles.laterButtonLabel}
                    onPress={() => router.back()}
                >
                    Maybe Later
                </Button>
            </View>

            <View style={{ height: 40 }} />
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: PALETTE.background,
    },
    header: {
        padding: 24,
        paddingTop: 48,
        paddingBottom: 16,
    },
    headerTitle: {
        color: PALETTE.textPrimary,
        fontWeight: '900',
        lineHeight: 40,
    },
    headerSubtitle: {
        color: PALETTE.textSecondary,
        marginTop: 12,
        lineHeight: 24,
    },
    card: {
        backgroundColor: PALETTE.card,
        marginHorizontal: 16,
        marginBottom: 20,
        padding: 24,
        borderRadius: 32, // Heavy pill-shape
        // Soft drop shadow
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 10 },
        shadowOpacity: 0.04,
        shadowRadius: 20,
        elevation: 2,
    },
    cardTitle: {
        color: PALETTE.textSecondary,
        fontWeight: '600',
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        marginBottom: 8,
    },
    listContainer: {
        marginTop: 0,
    },
    listItemTitle: {
        color: PALETTE.textPrimary,
        fontWeight: 'bold',
        fontSize: 16,
    },
    listItemDesc: {
        color: PALETTE.textSecondary,
        lineHeight: 20,
        marginTop: 4,
    },
    pricingCard: {
        backgroundColor: PALETTE.accentBlack,
        marginTop: 12,
        alignItems: 'center',
        paddingVertical: 32,
    },
    pricingSub: {
        color: '#E0E0E0',
        fontWeight: '600',
    },
    pricingTitle: {
        color: '#FFFFFF',
        fontWeight: '900',
        marginVertical: 16,
    },
    pricingMonth: {
        fontSize: 18,
        color: '#AAAAAA',
        fontWeight: 'normal',
    },
    subscribeButton: {
        marginTop: 16,
        backgroundColor: PALETTE.primary,
        borderRadius: 24,
        paddingVertical: 6,
        width: '100%',
    },
    subscribeButtonLabel: {
        color: '#FFFFFF',
        fontWeight: 'bold',
        fontSize: 16,
    },
    laterButton: {
        marginTop: 12,
    },
    laterButtonLabel: {
        color: '#888888',
        fontWeight: '600',
    }
});
