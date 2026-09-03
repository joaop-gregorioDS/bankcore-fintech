import SwiftUI
import UIKit

struct RootView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        Group {
            if app.isRestoring {
                ZStack {
                    Palette.ink.ignoresSafeArea()
                    VStack(spacing: 16) {
                        mark
                        Wordmark(size: 28)
                        ProgressView()
                            .tint(Palette.gold)
                    }
                }
            } else if app.isLoggedIn {
                MainTabs()
            } else {
                LoginView()
            }
        }
        .background(Palette.ink.ignoresSafeArea())
        .onAppear { configureChrome() }
        .sheet(item: Binding(
            get: { app.presentedReceipt },
            set: { app.presentedReceipt = $0 }
        )) { tx in
            ReceiptView(transaction: tx)
        }
    }

    private var mark: some View {
        Image(systemName: "shield")
            .font(.system(size: 22, weight: .medium))
            .foregroundStyle(Palette.gold)
            .frame(width: 48, height: 48)
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(Palette.gold, lineWidth: 1)
            )
    }

    private func configureChrome() {
        let tab = UITabBarAppearance()
        tab.configureWithOpaqueBackground()
        tab.backgroundColor = Palette.uiInk
        tab.shadowColor = Palette.uiLine
        let item = UITabBarItemAppearance()
        item.normal.iconColor = Palette.uiMute
        item.normal.titleTextAttributes = [.foregroundColor: Palette.uiMute]
        item.selected.iconColor = Palette.uiGold
        item.selected.titleTextAttributes = [.foregroundColor: Palette.uiGold]
        tab.stackedLayoutAppearance = item
        tab.inlineLayoutAppearance = item
        tab.compactInlineLayoutAppearance = item
        UITabBar.appearance().standardAppearance = tab
        UITabBar.appearance().scrollEdgeAppearance = tab

        let nav = UINavigationBarAppearance()
        nav.configureWithOpaqueBackground()
        nav.backgroundColor = Palette.uiInk
        nav.titleTextAttributes = [.foregroundColor: Palette.uiIvory]
        nav.largeTitleTextAttributes = [.foregroundColor: Palette.uiIvory]
        nav.shadowColor = Palette.uiLine
        UINavigationBar.appearance().standardAppearance = nav
        UINavigationBar.appearance().scrollEdgeAppearance = nav
        UINavigationBar.appearance().compactAppearance = nav
    }
}

struct MainTabs: View {
    @Environment(AppState.self) private var app

    var body: some View {
        @Bindable var app = app
        TabView(selection: $app.selectedTab) {
            HomeView()
                .tabItem { Label("Início", systemImage: "house") }
                .tag(AppState.MainTab.home)
            PixView()
                .tabItem { Label("Pix", systemImage: "arrow.left.arrow.right") }
                .tag(AppState.MainTab.pix)
            StatementView()
                .tabItem { Label("Extrato", systemImage: "list.bullet.rectangle") }
                .tag(AppState.MainTab.statement)
        }
    }
}
