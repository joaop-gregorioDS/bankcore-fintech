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
                        BrandMark(size: 56)
                        Wordmark(size: 28)
                        VersionLabel()
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
        .sheet(item: Binding(
            get: { app.presentedHub },
            set: { app.presentedHub = $0 }
        )) { hub in
            HubSheet(hub: hub)
        }
        .overlay(alignment: .top) {
            if let toast = app.toast {
                Text(toast)
                    .font(TypeScale.label)
                    .foregroundStyle(Palette.ivory)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .background(Palette.card)
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(Palette.gold.opacity(0.4), lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    .padding(.top, 56)
                    .padding(.horizontal, 20)
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .animation(.easeInOut(duration: 0.25), value: app.toast)
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
            CardsView()
                .tabItem { Label("Cartões", systemImage: "creditcard") }
                .tag(AppState.MainTab.cards)
            ProfileView()
                .tabItem { Label("Perfil", systemImage: "person") }
                .tag(AppState.MainTab.profile)
        }
    }
}
