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
}

// MARK: - Milestone Logic

struct MilestoneHelper {
    static let milestones = [1, 7, 14, 30, 60, 90, 180, 365, 730, 1095, 1460, 1825]

    static func calculate(daysSober: Int) -> (current: Int, next: Int, progress: Double) {
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

        // If past all milestones, next is the next yearly
        if daysSober >= (milestones.last ?? 1825) {
            current = daysSober - (daysSober % 365)
            if current == daysSober { current = daysSober - 365 }
            next = current + 365
        }

        let range = Double(next - current)
        let progress = range > 0 ? Double(daysSober - current) / range : 1.0
        return (current, next, min(max(progress, 0), 1))
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
            displayName: ""
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
                displayName: displayName
            )
        }

        let daysSober = Calendar.current.dateComponents([.day], from: sobrietyDate, to: Date()).day ?? 0
        let milestone = MilestoneHelper.calculate(daysSober: daysSober)

        return SobrietyEntry(
            date: Date(),
            daysSober: max(daysSober, 0),
            sobrietyDate: sobrietyDate,
            currentMilestone: milestone.current,
            nextMilestone: milestone.next,
            progress: milestone.progress,
            displayName: displayName
        )
    }
}

// MARK: - Widget Configuration

@main
struct SobrietyCounterWidget: Widget {
    let kind = "SobrietyCounterWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: SobrietyTimelineProvider()) { entry in
            SobrietyWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("Sobriety Counter")
        .description("Track your days in recovery.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
