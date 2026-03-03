import Foundation
import Capacitor
import WidgetKit

@objc(WidgetBridge)
public class WidgetBridge: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "WidgetBridge"
    public let jsName = "WidgetBridge"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "setWidgetData", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "clearWidgetData", returnType: CAPPluginReturnPromise)
    ]

    private let suiteName = "group.com.myrecoverypal.app"

    @objc func setWidgetData(_ call: CAPPluginCall) {
        guard let sobrietyDate = call.getString("sobrietyDate") else {
            call.reject("sobrietyDate is required")
            return
        }

        guard let defaults = UserDefaults(suiteName: suiteName) else {
            call.reject("Cannot access App Group")
            return
        }

        defaults.set(sobrietyDate, forKey: "sobriety_date")

        if let displayName = call.getString("displayName") {
            defaults.set(displayName, forKey: "display_name")
        }

        defaults.synchronize()

        if #available(iOS 14.0, *) {
            WidgetCenter.shared.reloadAllTimelines()
        }

        call.resolve(["success": true])
    }

    @objc func clearWidgetData(_ call: CAPPluginCall) {
        guard let defaults = UserDefaults(suiteName: suiteName) else {
            call.reject("Cannot access App Group")
            return
        }

        defaults.removeObject(forKey: "sobriety_date")
        defaults.removeObject(forKey: "display_name")
        defaults.synchronize()

        if #available(iOS 14.0, *) {
            WidgetCenter.shared.reloadAllTimelines()
        }

        call.resolve(["success": true])
    }
}
