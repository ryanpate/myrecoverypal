import SwiftUI
import WidgetKit

// MARK: - Color Constants

extension Color {
    static let mrpBlue = Color(red: 30/255, green: 77/255, blue: 139/255)       // #1e4d8b
    static let mrpLightBlue = Color(red: 45/255, green: 108/255, blue: 181/255) // #2d6cb5
    static let mrpGreen = Color(red: 82/255, green: 183/255, blue: 136/255)     // #52b788
    static let mrpGold = Color(red: 255/255, green: 193/255, blue: 7/255)       // #ffc107
    static let mrpGoldDark = Color(red: 255/255, green: 160/255, blue: 0/255)   // #ffa000
}

// MARK: - Background Gradient

private func widgetGradient(isMilestone: Bool) -> LinearGradient {
    if isMilestone {
        return LinearGradient(
            gradient: Gradient(colors: [
                Color(red: 255/255, green: 160/255, blue: 0/255),   // warm gold
                Color(red: 255/255, green: 193/255, blue: 7/255),   // bright gold
                Color(red: 255/255, green: 160/255, blue: 0/255)    // warm gold
            ]),
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    } else {
        return LinearGradient(
            gradient: Gradient(colors: [.mrpBlue, .mrpLightBlue]),
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}

// MARK: - Entry View (routes to correct size, applies background)

struct SobrietyWidgetEntryView: View {
    var entry: SobrietyEntry
    @Environment(\.widgetFamily) var family

    var body: some View {
        if #available(iOSApplicationExtension 17.0, *) {
            widgetContent
                .containerBackground(for: .widget) {
                    widgetGradient(isMilestone: entry.isMilestoneDay)
                }
        } else {
            ZStack {
                widgetGradient(isMilestone: entry.isMilestoneDay)
                widgetContent
            }
        }
    }

    @ViewBuilder
    private var widgetContent: some View {
        switch family {
        case .systemSmall:
            SmallWidgetView(entry: entry)
        case .systemMedium:
            MediumWidgetView(entry: entry)
        default:
            SmallWidgetView(entry: entry)
        }
    }
}

// MARK: - Small Widget

struct SmallWidgetView: View {
    var entry: SobrietyEntry

    var body: some View {
        Group {
            if entry.sobrietyDate != nil {
                VStack(spacing: 4) {
                    if entry.isMilestoneDay {
                        Text("🎉")
                            .font(.system(size: 20))
                    }

                    Text("\(entry.daysSober)")
                        .font(.system(size: 48, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                        .minimumScaleFactor(0.5)
                        .lineLimit(1)

                    Text(entry.daysSober == 1 ? "day sober" : "days sober")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.white.opacity(0.85))

                    Spacer().frame(height: 4)

                    Text(milestoneText)
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(entry.isMilestoneDay ? .white : .mrpGreen)
                        .lineLimit(1)
                }
                .padding(.vertical, 12)
            } else {
                VStack(spacing: 8) {
                    Image(systemName: "heart.circle.fill")
                        .font(.system(size: 32))
                        .foregroundColor(.white.opacity(0.8))
                    Text("Open app to\nset your date")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.white.opacity(0.85))
                        .multilineTextAlignment(.center)
                }
            }
        }
        .widgetURL(URL(string: "myrecoverypal://social-feed"))
    }

    private var milestoneText: String {
        let daysTo = entry.nextMilestone - entry.daysSober
        if entry.isMilestoneDay { return "🏆 Milestone reached!" }
        if daysTo <= 0 { return "Milestone reached!" }
        return "\(daysTo)d to \(formatMilestone(entry.nextMilestone))"
    }

    private func formatMilestone(_ days: Int) -> String {
        if days >= 365 {
            let years = days / 365
            return "\(years) year\(years > 1 ? "s" : "")"
        } else if days >= 30 {
            let months = days / 30
            return "\(months) month\(months > 1 ? "s" : "")"
        } else {
            return "\(days) days"
        }
    }
}

// MARK: - Medium Widget

struct MediumWidgetView: View {
    var entry: SobrietyEntry

    private var ringAccentColor: Color {
        entry.isMilestoneDay ? .mrpGold : .mrpGreen
    }

    var body: some View {
        Group {
            if let sobrietyDate = entry.sobrietyDate {
                HStack(spacing: 16) {
                    // Left: Progress Ring with years/months breakdown
                    ZStack {
                        Circle()
                            .stroke(Color.white.opacity(0.2), lineWidth: 8)
                        Circle()
                            .trim(from: 0, to: CGFloat(entry.isMilestoneDay ? 1.0 : entry.progress))
                            .stroke(ringAccentColor, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                            .rotationEffect(.degrees(-90))
                        VStack(spacing: 2) {
                            if entry.isMilestoneDay {
                                Text("🎉")
                                    .font(.system(size: 14))
                            }
                            if entry.yearsSober > 0 {
                                Text("\(entry.yearsSober)")
                                    .font(.system(size: 28, weight: .bold, design: .rounded))
                                    .foregroundColor(.white)
                                Text(entry.yearsSober == 1 ? "year" : "years")
                                    .font(.system(size: 10, weight: .medium))
                                    .foregroundColor(.white.opacity(0.8))
                                if !entry.isMilestoneDay {
                                    Text("\(entry.monthsSober) mo")
                                        .font(.system(size: 11, weight: .semibold))
                                        .foregroundColor(ringAccentColor)
                                }
                            } else if entry.monthsSober > 0 {
                                Text("\(entry.monthsSober)")
                                    .font(.system(size: 28, weight: .bold, design: .rounded))
                                    .foregroundColor(.white)
                                Text(entry.monthsSober == 1 ? "month" : "months")
                                    .font(.system(size: 10, weight: .medium))
                                    .foregroundColor(.white.opacity(0.8))
                            } else {
                                Text("\(entry.daysSober)")
                                    .font(.system(size: 28, weight: .bold, design: .rounded))
                                    .foregroundColor(.white)
                                    .minimumScaleFactor(0.5)
                                    .lineLimit(1)
                                Text(entry.daysSober == 1 ? "day" : "days")
                                    .font(.system(size: 10, weight: .medium))
                                    .foregroundColor(.white.opacity(0.8))
                            }
                        }
                    }
                    .frame(width: 90, height: 90)

                    // Right: Details (vertically centered)
                    VStack(spacing: 6) {
                        // Days sober title
                        if entry.isMilestoneDay {
                            Text("🏆 Milestone!")
                                .font(.system(size: 18, weight: .bold))
                                .foregroundColor(.white)
                        }

                        Text(entry.daysSober == 1 ? "1 Day Sober" : "\(formatNumber(entry.daysSober)) Days Sober")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(.white)

                        // Sobriety date
                        HStack(spacing: 4) {
                            Image(systemName: "calendar")
                                .font(.system(size: 10))
                                .foregroundColor(.white.opacity(0.6))
                            Text("Since \(formatDate(sobrietyDate))")
                                .font(.system(size: 11, weight: .medium))
                                .foregroundColor(.white.opacity(0.7))
                        }

                        // Next milestone or celebration
                        let daysTo = entry.nextMilestone - entry.daysSober
                        if entry.isMilestoneDay {
                            HStack(spacing: 4) {
                                Image(systemName: "star.fill")
                                    .font(.system(size: 10))
                                    .foregroundColor(.white)
                                Text(milestoneReachedLabel)
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(.white)
                            }
                        } else if daysTo > 0 {
                            HStack(spacing: 4) {
                                Image(systemName: "flag.fill")
                                    .font(.system(size: 10))
                                    .foregroundColor(.mrpGreen)
                                Text("\(daysTo) \(daysTo == 1 ? "day" : "days") to \(formatMilestone(entry.nextMilestone))")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundColor(.white.opacity(0.85))
                            }
                        }

                        // Progress bar (hide on milestone day — ring is full)
                        if !entry.isMilestoneDay {
                            GeometryReader { geo in
                                ZStack(alignment: .leading) {
                                    RoundedRectangle(cornerRadius: 3)
                                        .fill(Color.white.opacity(0.2))
                                        .frame(height: 6)
                                    RoundedRectangle(cornerRadius: 3)
                                        .fill(Color.mrpGreen)
                                        .frame(width: geo.size.width * CGFloat(entry.progress), height: 6)
                                }
                            }
                            .frame(height: 6)
                        }
                    }
                    .frame(maxWidth: .infinity)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            } else {
                HStack(spacing: 16) {
                    Image(systemName: "heart.circle.fill")
                        .font(.system(size: 40))
                        .foregroundColor(.white.opacity(0.8))
                    VStack(alignment: .leading, spacing: 4) {
                        Text("MyRecoveryPal")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                        Text("Open the app to set your sobriety date and start tracking.")
                            .font(.system(size: 12))
                            .foregroundColor(.white.opacity(0.8))
                    }
                }
                .padding(.horizontal, 16)
            }
        }
        .widgetURL(URL(string: "myrecoverypal://social-feed"))
    }

    private var milestoneReachedLabel: String {
        if entry.yearsSober > 0 {
            return "\(entry.yearsSober) \(entry.yearsSober == 1 ? "year" : "years") sober!"
        } else if entry.monthsSober > 0 {
            return "\(entry.monthsSober) \(entry.monthsSober == 1 ? "month" : "months") sober!"
        } else {
            return "\(entry.daysSober) \(entry.daysSober == 1 ? "day" : "days") sober!"
        }
    }

    private func formatNumber(_ n: Int) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        return formatter.string(from: NSNumber(value: n)) ?? "\(n)"
    }

    private func formatMilestone(_ days: Int) -> String {
        if days >= 365 {
            let years = days / 365
            return "\(years) year\(years > 1 ? "s" : "")"
        } else if days >= 30 {
            let months = days / 30
            return "\(months) month\(months > 1 ? "s" : "")"
        } else {
            return "\(days) days"
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d, yyyy"
        return formatter.string(from: date)
    }
}

// MARK: - Previews

struct SobrietyWidget_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            // Normal state — small
            SobrietyWidgetEntryView(entry: SobrietyEntry(
                date: Date(), daysSober: 2921, sobrietyDate: Date(),
                currentMilestone: 2555, nextMilestone: 2922, progress: 0.99, displayName: "Ryan",
                yearsSober: 7, monthsSober: 11, isMilestoneDay: false
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
            .previewDisplayName("Small")

            // Normal state — medium
            SobrietyWidgetEntryView(entry: SobrietyEntry(
                date: Date(), daysSober: 2921, sobrietyDate: Date(),
                currentMilestone: 2555, nextMilestone: 2922, progress: 0.99, displayName: "Ryan",
                yearsSober: 7, monthsSober: 11, isMilestoneDay: false
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))
            .previewDisplayName("Medium")

            // Milestone day — small
            SobrietyWidgetEntryView(entry: SobrietyEntry(
                date: Date(), daysSober: 2922, sobrietyDate: Date(),
                currentMilestone: 2922, nextMilestone: 3287, progress: 0.0, displayName: "Ryan",
                yearsSober: 8, monthsSober: 0, isMilestoneDay: true
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
            .previewDisplayName("Small — Milestone")

            // Milestone day — medium
            SobrietyWidgetEntryView(entry: SobrietyEntry(
                date: Date(), daysSober: 2922, sobrietyDate: Date(),
                currentMilestone: 2922, nextMilestone: 3287, progress: 0.0, displayName: "Ryan",
                yearsSober: 8, monthsSober: 0, isMilestoneDay: true
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))
            .previewDisplayName("Medium — Milestone")

            // Empty state
            SobrietyWidgetEntryView(entry: SobrietyEntry(
                date: Date(), daysSober: 0, sobrietyDate: nil,
                currentMilestone: 0, nextMilestone: 1, progress: 0, displayName: "",
                yearsSober: 0, monthsSober: 0, isMilestoneDay: false
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
            .previewDisplayName("Empty")
        }
    }
}
