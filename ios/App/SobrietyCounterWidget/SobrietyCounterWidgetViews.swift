import SwiftUI
import WidgetKit

// MARK: - Color Constants

extension Color {
    static let mrpBlue = Color(red: 30/255, green: 77/255, blue: 139/255)       // #1e4d8b
    static let mrpLightBlue = Color(red: 45/255, green: 108/255, blue: 181/255) // #2d6cb5
    static let mrpGreen = Color(red: 82/255, green: 183/255, blue: 136/255)     // #52b788
}

// MARK: - Entry View (routes to correct size)

struct SobrietyWidgetEntryView: View {
    var entry: SobrietyEntry
    @Environment(\.widgetFamily) var family

    var body: some View {
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
        ZStack {
            LinearGradient(
                gradient: Gradient(colors: [.mrpBlue, .mrpLightBlue]),
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            if entry.sobrietyDate != nil {
                VStack(spacing: 4) {
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
                        .foregroundColor(.mrpGreen)
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

    var body: some View {
        ZStack {
            LinearGradient(
                gradient: Gradient(colors: [.mrpBlue, .mrpLightBlue]),
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            if entry.sobrietyDate != nil {
                HStack(spacing: 16) {
                    // Left: Progress Ring
                    ZStack {
                        Circle()
                            .stroke(Color.white.opacity(0.2), lineWidth: 8)
                        Circle()
                            .trim(from: 0, to: CGFloat(entry.progress))
                            .stroke(Color.mrpGreen, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                            .rotationEffect(.degrees(-90))
                        VStack(spacing: 0) {
                            Text("\(entry.daysSober)")
                                .font(.system(size: 28, weight: .bold, design: .rounded))
                                .foregroundColor(.white)
                                .minimumScaleFactor(0.5)
                                .lineLimit(1)
                            Text("days")
                                .font(.system(size: 10, weight: .medium))
                                .foregroundColor(.white.opacity(0.8))
                        }
                    }
                    .frame(width: 90, height: 90)

                    // Right: Details
                    VStack(alignment: .leading, spacing: 6) {
                        Text("MyRecoveryPal")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundColor(.white.opacity(0.6))
                            .textCase(.uppercase)
                            .tracking(0.5)

                        Text(entry.daysSober == 1 ? "1 Day Sober" : "\(entry.daysSober) Days Sober")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(.white)

                        Spacer().frame(height: 2)

                        // Next milestone
                        let daysTo = entry.nextMilestone - entry.daysSober
                        if daysTo > 0 {
                            HStack(spacing: 4) {
                                Image(systemName: "flag.fill")
                                    .font(.system(size: 10))
                                    .foregroundColor(.mrpGreen)
                                Text("\(daysTo) days to \(formatMilestone(entry.nextMilestone))")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundColor(.white.opacity(0.85))
                            }
                        } else {
                            HStack(spacing: 4) {
                                Image(systemName: "star.fill")
                                    .font(.system(size: 10))
                                    .foregroundColor(.mrpGreen)
                                Text("Milestone reached!")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundColor(.mrpGreen)
                            }
                        }

                        // Progress bar
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
                    .frame(maxWidth: .infinity, alignment: .leading)
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

// MARK: - Previews

struct SobrietyWidget_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            SmallWidgetView(entry: SobrietyEntry(
                date: Date(), daysSober: 42, sobrietyDate: Date(),
                currentMilestone: 30, nextMilestone: 60, progress: 0.4, displayName: "Ryan"
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))

            MediumWidgetView(entry: SobrietyEntry(
                date: Date(), daysSober: 42, sobrietyDate: Date(),
                currentMilestone: 30, nextMilestone: 60, progress: 0.4, displayName: "Ryan"
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))

            // Empty state
            SmallWidgetView(entry: SobrietyEntry(
                date: Date(), daysSober: 0, sobrietyDate: nil,
                currentMilestone: 0, nextMilestone: 1, progress: 0, displayName: ""
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
        }
    }
}
