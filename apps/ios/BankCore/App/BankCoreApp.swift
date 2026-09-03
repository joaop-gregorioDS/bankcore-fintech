import SwiftUI

@main
struct BankCoreApp: App {
    @State private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(appState)
                .preferredColorScheme(.dark)
                .tint(Palette.gold)
                .task { await appState.bootstrap() }
        }
    }
}
