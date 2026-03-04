import WidgetKit
import SwiftUI

// MARK: - Data Model

struct SobrietyEntry: TimelineEntry {
    let date: Date
    let daysSober: Int
    let sobrietyDate: Date?
    let currentMilestone: Int
    let nextMilestone: Int
    let progress: Double
    let displayName: String
    let yearsSober: Int
    let monthsSober: Int
    let isMilestoneDay: Bool
}

// MARK: - Milestone Logic

struct MilestoneHelper {
    static let milestones = [1, 7, 14, 30, 60, 90, 180, 365, 730, 1095, 1460, 1825]

    static func calculate(daysSober: Int, sobrietyDate: Date?) -> (current: Int, next: Int, progress: Double) {
        var current = 0
        var next = milestones.first ?? 1

        for m in milestones {
            if daysSober >= m {
                current = m
            } else {
                next = m
                break
            }
        }

        // Past all fixed milestones: use calendar-based year anniversaries
        if daysSober >= (milestones.last ?? 1825), let sobrietyDate = sobrietyDate {
            let calendar = Calendar.current
            let today = calendar.startOfDay(for: Date())
            let startDay = calendar.startOfDay(for: sobrietyDate)
            let yearsSober = calendar.dateComponents([.year], from: startDay, to: today).year ?? 0

            // Last anniversary (yearsSober years after sobriety date)
            let lastAnniversary = calendar.date(byAdding: .year, value: yearsSober, to: startDay) ?? today
            // Next anniversary
            let nextAnniversary = calendar.date(byAdding: .year, value: yearsSober + 1, to: startDay) ?? today

            let daysFromStart = calendar.dateComponents([.day], from: startDay, to: lastAnniversary).day ?? daysSober
            let daysToNext = calendar.dateComponents([.day], from: startDay, to: nextAnniversary).day ?? (daysSober + 365)

            current = daysFromStart
            next = daysToNext

            // If today IS the anniversary, show it as reached
            if lastAnniversary == today {
                current = daysFromStart
            }
        }

        let range = Double(next - current)
        let progress = range > 0 ? Double(daysSober - current) / range : 1.0
        return (current, next, min(max(progress, 0), 1))
    }

    /// Check if today is exactly a milestone day
    static func isMilestoneDay(daysSober: Int, sobrietyDate: Date?) -> Bool {
        // Check fixed milestones
        if milestones.contains(daysSober) {
            return true
        }
        // Check year anniversaries for long-term sobriety
        if let sobrietyDate = sobrietyDate {
            let calendar = Calendar.current
            let today = calendar.startOfDay(for: Date())
            let startDay = calendar.startOfDay(for: sobrietyDate)
            let components = calendar.dateComponents([.month, .day], from: startDay)
            let todayComponents = calendar.dateComponents([.month, .day], from: today)
            // Anniversary if same month+day and at least 1 year
            if components.month == todayComponents.month && components.day == todayComponents.day && daysSober >= 365 {
                return true
            }
        }
        return false
    }
}

// MARK: - Timeline Provider

struct SobrietyTimelineProvider: TimelineProvider {
    private let suiteName = "group.com.myrecoverypal.app"

    func placeholder(in context: Context) -> SobrietyEntry {
        SobrietyEntry(
            date: Date(),
            daysSober: 42,
            sobrietyDate: nil,
            currentMilestone: 30,
            nextMilestone: 60,
            progress: 0.4,
            displayName: "",
            yearsSober: 0,
            monthsSober: 1,
            isMilestoneDay: false
        )
    }

    func getSnapshot(in context: Context, completion: @escaping (SobrietyEntry) -> Void) {
        completion(makeEntry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SobrietyEntry>) -> Void) {
        let entry = makeEntry()

        // Refresh at midnight to update the day count
        let calendar = Calendar.current
        let tomorrow = calendar.startOfDay(for: calendar.date(byAdding: .day, value: 1, to: Date())!)
        let timeline = Timeline(entries: [entry], policy: .after(tomorrow))
        completion(timeline)
    }

    private func makeEntry() -> SobrietyEntry {
        let defaults = UserDefaults(suiteName: suiteName)
        let dateString = defaults?.string(forKey: "sobriety_date") ?? ""
        let displayName = defaults?.string(forKey: "display_name") ?? ""

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"

        guard !dateString.isEmpty, let sobrietyDate = formatter.date(from: dateString) else {
            return SobrietyEntry(
                date: Date(),
                daysSober: 0,
                sobrietyDate: nil,
                currentMilestone: 0,
                nextMilestone: 1,
                progress: 0,
                displayName: displayName,
                yearsSober: 0,
                monthsSober: 0,
                isMilestoneDay: false
            )
        }

        let calendar = Calendar.current
        let daysSober = calendar.dateComponents([.day], from: sobrietyDate, to: Date()).day ?? 0
        let milestone = MilestoneHelper.calculate(daysSober: daysSober, sobrietyDate: sobrietyDate)
        let components = calendar.dateComponents([.year, .month], from: sobrietyDate, to: Date())
        let isMilestone = MilestoneHelper.isMilestoneDay(daysSober: daysSober, sobrietyDate: sobrietyDate)

        return SobrietyEntry(
            date: Date(),
            daysSober: max(daysSober, 0),
            sobrietyDate: sobrietyDate,
            currentMilestone: milestone.current,
            nextMilestone: milestone.next,
            progress: milestone.progress,
            displayName: displayName,
            yearsSober: components.year ?? 0,
            monthsSober: components.month ?? 0,
            isMilestoneDay: isMilestone
        )
    }
}

// MARK: - Widget Configuration

@main
struct SobrietyCounterWidget: Widget {
    let kind = "SobrietyCounterWidget"

    var body: some WidgetConfiguration {
        let config = StaticConfiguration(kind: kind, provider: SobrietyTimelineProvider()) { entry in
            SobrietyWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("Sobriety Counter")
        .description("Track your days in recovery.")
        .supportedFamilies([.systemSmall, .systemMedium])

        if #available(iOSApplicationExtension 17.0, *) {
            return config.contentMarginsDisabled()
        } else {
            return config
        }
    }
}
