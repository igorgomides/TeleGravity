import { useLocalSearchParams, useRouter } from 'expo-router';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Chip, ProgressBar, Text } from 'react-native-paper';

// Custom Palette based on user request (Green, White, Black accents)
const PALETTE = {
    background: '#F4F7F6', // Very subtle off-white to make pure white cards pop
    card: '#FFFFFF',
    primary: '#0CD179', // Vibrant Green from the Neobankless reference
    textPrimary: '#111111', // Deep Black for headings
    textSecondary: '#666666', // Grey for labels
    error: '#FF4D4D', // Soft Red for negative/debt
    accentBlack: '#1A1A1A', // Used for some buttons/accents
};

export default function SnapshotScreen() {
    const router = useRouter();
    const params = useLocalSearchParams();

    // Stage 1: Incomes
    const personalIncome = Number(params.personalIncome || 0);
    const spouseIncome = Number(params.spouseIncome || 0);
    const otherIncome = Number(params.otherIncome || 0);
    const totalIncome = personalIncome + spouseIncome + otherIncome;

    // Expenses
    const fixedExpenses = Number(params.fixedMonthlyExpenses || 0);

    // Stage 2: Debts
    const mortgageDebt = Number(params.mortgageDebt || 0);
    const mortgageRate = params.mortgageInterestRate;
    const carLoanDebt = Number(params.carLoanDebt || 0);
    const carLoanRate = params.carLoanInterestRate;
    const creditCardDebt = Number(params.creditCardDebt || 0);
    const creditCardRate = params.creditCardInterestRate;
    const creditCardLimit = Number(params.creditCardLimit || 0);
    const lineOfCreditBalance = Number(params.lineOfCreditBalance || 0);
    const lineOfCreditRate = params.lineOfCreditInterestRate;
    const totalDebts = mortgageDebt + carLoanDebt + creditCardDebt + lineOfCreditBalance;

    // Stage 3 & 4: Deep Data
    const banks = params.banksUsed ? String(params.banksUsed).split(',').map(b => b.trim()) : [];
    const hasRRSP = params.hasRRSP === 'true';
    const hasChildren = params.hasChildren === 'true';
    const usesChildBenefits = params.usesChildBenefits === 'true';
    const spendingSummary = String(params.spendingHabitsSummary || '');

    const cashflow = totalIncome - fixedExpenses;
    const isPositive = cashflow > 0;

    // Simple progress calculation to keep it light
    const expenseRatio = totalIncome > 0 ? Math.min(fixedExpenses / totalIncome, 1) : 0;
    const healthColor = isPositive ? PALETTE.primary : PALETTE.error;

    return (
        <ScrollView style={styles.container}>
            <View style={styles.header}>
                <Text variant="headlineMedium" style={styles.headerTitle}>
                    Your Detailed Snapshot
                </Text>
                <Text variant="bodyLarge" style={styles.headerSubtitle}>
                    A robust view of your multi-stream cashflow and financial profile.
                </Text>
            </View>

            {/* STAGE 1 CARD - CASHFLOW */}
            <View style={styles.card}>
                <Text variant="titleMedium" style={styles.cardTitle}>Monthly Cashflow</Text>

                <View style={styles.amountRow}>
                    <Text variant="displayMedium" style={[styles.mainAmount, { color: healthColor }]}>
                        {isPositive ? '+' : ''}${cashflow.toLocaleString()}
                    </Text>
                    <Text variant="labelLarge" style={styles.label}>/ month</Text>
                </View>

                <Text variant="bodySmall" style={styles.progressLabel}>
                    Expenses vs Total Income
                </Text>
                <ProgressBar progress={expenseRatio} color={healthColor} style={styles.progressBar} />

                <View style={styles.detailsRow}>
                    <View>
                        <Text variant="labelLarge" style={styles.label}>Total Income</Text>
                        <Text variant="titleLarge" style={styles.value}>${totalIncome.toLocaleString()}</Text>

                        {(spouseIncome > 0 || otherIncome > 0) && (
                            <View style={{ marginTop: 8 }}>
                                <Text variant="bodySmall" style={styles.subLabel}>Personal: ${personalIncome.toLocaleString()}</Text>
                                {spouseIncome > 0 && <Text variant="bodySmall" style={styles.subLabel}>Spouse: ${spouseIncome.toLocaleString()}</Text>}
                                {otherIncome > 0 && <Text variant="bodySmall" style={styles.subLabel}>Other: ${otherIncome.toLocaleString()}</Text>}
                            </View>
                        )}
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                        <Text variant="labelLarge" style={styles.label}>Fixed Expenses</Text>
                        <Text variant="titleLarge" style={styles.value}>${fixedExpenses.toLocaleString()}</Text>
                    </View>
                </View>
            </View>

            {/* STAGE 2 CARD - DEBTS */}
            <View style={styles.card}>
                <Text variant="titleMedium" style={styles.cardTitle}>Active Debts Overview</Text>
                <Text variant="displayMedium" style={[styles.mainAmount, { color: totalDebts > 0 ? PALETTE.error : PALETTE.primary }]}>
                    ${totalDebts.toLocaleString()}
                </Text>

                <View style={styles.divider} />

                <View style={styles.debtItem}>
                    <View>
                        <Text variant="titleMedium" style={styles.debtTitle}>Mortgage</Text>
                        {mortgageRate && mortgageRate !== 'null' && <Text variant="bodySmall" style={styles.interestLabel}>Wait, you pay {mortgageRate}%?</Text>}
                    </View>
                    <Text variant="titleMedium" style={styles.value}>${mortgageDebt.toLocaleString()}</Text>
                </View>

                <View style={styles.debtItem}>
                    <View>
                        <Text variant="titleMedium" style={styles.debtTitle}>Car Loans</Text>
                        {carLoanRate && carLoanRate !== 'null' && <Text variant="bodySmall" style={styles.interestLabel}>Wait, you pay {carLoanRate}%?</Text>}
                    </View>
                    <Text variant="titleMedium" style={styles.value}>${carLoanDebt.toLocaleString()}</Text>
                </View>

                <View style={styles.debtItem}>
                    <View>
                        <Text variant="titleMedium" style={styles.debtTitle}>Credit Cards</Text>
                        {creditCardRate && creditCardRate !== 'null' && <Text variant="bodySmall" style={styles.interestLabel}>Wait, you pay {creditCardRate}%?</Text>}
                        {creditCardLimit > 0 && <Text variant="bodySmall" style={styles.subLabel}>Limit: ${creditCardLimit.toLocaleString()}</Text>}
                    </View>
                    <Text variant="titleMedium" style={[styles.value, { color: creditCardDebt > 0 ? PALETTE.error : PALETTE.textPrimary }]}>
                        ${creditCardDebt.toLocaleString()}
                    </Text>
                </View>

                {lineOfCreditBalance > 0 && (
                    <View style={styles.debtItem}>
                        <View>
                            <Text variant="titleMedium" style={styles.debtTitle}>Line of Credit</Text>
                            {lineOfCreditRate && lineOfCreditRate !== 'null' && <Text variant="bodySmall" style={styles.interestLabel}>{lineOfCreditRate}% / year</Text>}
                        </View>
                        <Text variant="titleMedium" style={styles.value}>${lineOfCreditBalance.toLocaleString()}</Text>
                    </View>
                )}
            </View>

            {/* STAGE 3 & 4 CARD: ECOSYSTEM AND HABITS */}
            <View style={styles.card}>
                <Text variant="titleMedium" style={styles.cardTitle}>Your Ecosystem Profile</Text>

                {banks.length > 0 && banks[0] !== 'undefined' && (
                    <View style={{ marginTop: 16 }}>
                        <Text variant="labelLarge" style={styles.label}>Active Banks</Text>
                        <View style={styles.chipContainer}>
                            {banks.map((bank, index) => (
                                <Chip key={index} mode="flat" style={styles.chip} textStyle={styles.chipText}>{bank}</Chip>
                            ))}
                        </View>
                    </View>
                )}

                <View style={styles.divider} />

                <Text variant="labelLarge" style={[styles.label, { marginBottom: 16 }]}>Canadian Benefits Opportunities</Text>
                <View style={styles.benefitItem}>
                    <Text variant="bodyLarge" style={styles.value}>Using RRSP for Tax Deduction?</Text>
                    <View style={[styles.statusBadge, { backgroundColor: hasRRSP ? PALETTE.primary : PALETTE.error }]}>
                        <Text style={styles.statusText}>{hasRRSP ? 'YES' : 'NO'}</Text>
                    </View>
                </View>
                {hasChildren && (
                    <View style={styles.benefitItem}>
                        <Text variant="bodyLarge" style={styles.value}>Using Gov. Child Price-Matching (RESP)?</Text>
                        <View style={[styles.statusBadge, { backgroundColor: usesChildBenefits ? PALETTE.primary : PALETTE.error }]}>
                            <Text style={styles.statusText}>{usesChildBenefits ? 'YES' : 'NO'}</Text>
                        </View>
                    </View>
                )}

                {spendingSummary && spendingSummary !== 'undefined' && spendingSummary.length > 5 && (
                    <View style={styles.insightBox}>
                        <Text variant="labelMedium" style={styles.insightLabel}>Lifestyle Insight</Text>
                        <Text variant="bodyMedium" style={styles.insightText}>"{spendingSummary}"</Text>
                    </View>
                )}
            </View>

            {/* UPSELL TEASER (Black accent card) */}
            <View style={[styles.card, styles.teaserCard]}>
                <Text variant="headlineSmall" style={styles.teaserTitle}>
                    Want to optimize this?
                </Text>
                <Text variant="bodyLarge" style={styles.teaserSubtitle}>
                    Based on your profile, we can restructure your {totalDebts > 0 ? 'debts' : 'cashflow'} and unlock specific Canadian benefits to easily render <Text style={{ fontWeight: 'bold', color: PALETTE.primary }}>13% more value</Text> out of your money this year.
                </Text>
                <Button
                    mode="contained"
                    style={styles.actionButton}
                    labelStyle={styles.actionButtonLabel}
                    onPress={() => router.push('/upsell')}
                >
                    Unlock Pro Strategy
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
    },
    headerSubtitle: {
        color: PALETTE.textSecondary,
        marginTop: 8,
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
    },
    amountRow: {
        flexDirection: 'row',
        alignItems: 'baseline',
        marginTop: 12,
        gap: 8,
    },
    mainAmount: {
        fontWeight: '900',
    },
    label: {
        color: PALETTE.textSecondary,
        fontWeight: '500',
    },
    value: {
        color: PALETTE.textPrimary,
        fontWeight: 'bold',
    },
    subLabel: {
        color: PALETTE.textSecondary,
    },
    progressLabel: {
        marginTop: 20,
        marginBottom: 8,
        color: PALETTE.textSecondary,
        fontWeight: '500',
    },
    progressBar: {
        height: 12,
        borderRadius: 6,
        backgroundColor: '#EAEAEA',
    },
    detailsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 24,
    },
    divider: {
        height: 1,
        backgroundColor: '#F0F0F0',
        marginVertical: 20,
    },
    debtItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 10,
    },
    debtTitle: {
        color: PALETTE.textPrimary,
        fontWeight: '700',
    },
    interestLabel: {
        color: PALETTE.error,
        fontWeight: '600',
        marginTop: 2,
    },
    chipContainer: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 8,
        marginTop: 8,
    },
    chip: {
        backgroundColor: '#E8F5E9', // Very light green
        borderRadius: 16,
    },
    chipText: {
        color: PALETTE.primary,
        fontWeight: 'bold',
    },
    benefitItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
    },
    statusBadge: {
        paddingHorizontal: 12,
        paddingVertical: 4,
        borderRadius: 12,
    },
    statusText: {
        color: '#FFFFFF',
        fontWeight: '900',
        fontSize: 12,
    },
    insightBox: {
        marginTop: 24,
        backgroundColor: '#F9F9F9',
        padding: 16,
        borderRadius: 16,
        borderLeftWidth: 4,
        borderLeftColor: PALETTE.primary,
    },
    insightLabel: {
        color: PALETTE.primary,
        fontWeight: 'bold',
        textTransform: 'uppercase',
    },
    insightText: {
        color: PALETTE.textSecondary,
        fontStyle: 'italic',
        lineHeight: 22,
        marginTop: 4,
    },
    teaserCard: {
        backgroundColor: PALETTE.accentBlack,
        marginTop: 12,
    },
    teaserTitle: {
        color: '#FFFFFF',
        fontWeight: '900',
    },
    teaserSubtitle: {
        color: '#CCCCCC',
        marginTop: 12,
        lineHeight: 24,
    },
    actionButton: {
        marginTop: 32,
        backgroundColor: PALETTE.primary,
        borderRadius: 24,
        paddingVertical: 6,
    },
    actionButtonLabel: {
        color: '#FFFFFF',
        fontWeight: 'bold',
        fontSize: 16,
    }
});
