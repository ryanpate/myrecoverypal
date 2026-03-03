import UIKit
import Capacitor
import WidgetKit

class MyViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        bridge?.registerPluginInstance(WidgetBridge())

        // Refresh widget with persisted App Group data on app launch
        // (data survives across launches, so widget shows info before JS loads)
        if #available(iOS 14.0, *) {
            WidgetCenter.shared.reloadAllTimelines()
        }
    }
}
