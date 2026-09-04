import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

Panel {
  id: root
  moduleName: "digitalbase.hyper"
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  ipcTarget: "digitalbase.hyper"
  manageIpc: false
  IpcHandler {
    target: "digitalbase.hyper"
    function open(): void { root.open() }
    function close(): void { root.close() }
    function toggle(): void { root.toggle() }
    function add(): void { root.open(); root.picking = true; root.selectedApp = null; root.refreshApps() }
    function info(): string { return JSON.stringify({view: root.picking ? "apps" : "shortcuts", apps: root.apps.length, shortcuts: root.rows, error: root.error}) }
  }
  property var state: ({shortcuts: {}, external: [], active: false, options: null})
  property string error: ""
  property bool picking: false
  property string action: "status"
  property var selectedApp: null
  property var apps: []
  readonly property var library: bar && bar.shell ? bar.shell.appLibrary : null
  readonly property var rows: {
    var result = []
    var shortcuts = state.shortcuts || {}
    Object.keys(shortcuts).sort().forEach(function(key) {
      result.push({key: key, name: shortcuts[key].name, id: shortcuts[key].id, external: false})
    })
    return result.concat(state.external || [])
  }

  function refreshApps() {
    apps = library ? library.sortedEntries(search.text).map(function(app) {
      return {id: app.id, name: library.entryName(app), icon: app.icon}
    }) : []
  }
  function request(args) {
    if (backend.running) return
    error = ""
    action = args[0]
    backend.command = ["python3", Qt.resolvedUrl("hyper.py").toString().replace(/^file:\/\//, "")].concat(args)
    backend.running = true
  }
  onOpenedChanged: if (opened) {
    picking = false
    selectedApp = null
    request(["status"])
  }
  Connections {
    target: root.library
    function onAppsChanged() { if (root.opened) root.refreshApps() }
  }
  Process {
    id: backend
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (result.ok) {
            root.state = result
            if (root.action === "assign") { root.picking = false; root.selectedApp = null }
          }
          else root.error = result.error
        } catch (e) { root.error = "Could not read Hyper settings. " + text }
      }
    }
    stderr: StdioCollector { onStreamFinished: if (text.trim()) root.error = text.trim() }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "✦"
    fontSize: Style.bar.iconFont * 1.3
    onPressed: root.toggle()
  }
  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: content
    contentWidth: panel.fittedContentWidth(480)
    contentHeight: panel.fittedContentHeight(570)

    FocusScope {
      id: content
      anchors.fill: parent
      Keys.onEscapePressed: {
        if (root.picking) { root.picking = false; root.selectedApp = null }
        else root.close()
      }
      ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
          Layout.fillWidth: true
          Text { text: "✦"; color: Color.accent; font.pixelSize: 36 }
          ColumnLayout {
            Layout.fillWidth: true
            Text { text: "Hyper"; color: Color.foreground; font.family: Style.font.family; font.pixelSize: 24; font.bold: true }
            Text { text: root.state.active ? "Caps Lock is your Hyper key" : "Your apps, one shortcut away"; color: Color.foreground; opacity: 0.65; font.pixelSize: 13 }
          }
          Button { text: "Close"; focusable: true; onClicked: root.close() }
        }
        Text {
          Layout.fillWidth: true
          visible: !root.state.active
          text: "Use Caps Lock as ✦. Hold it and press a key to launch an app. Caps Lock will stop toggling uppercase letters."
          wrapMode: Text.WordWrap; color: Color.foreground; font.pixelSize: 14
        }
        Button {
          visible: !root.state.active
          text: "Set up Hyper"; bordered: true; focusable: true
          enabled: !backend.running
          onClicked: root.request(["enable"])
        }
        Text {
          Layout.fillWidth: true
          visible: root.error !== ""
          text: root.error; textFormat: Text.PlainText
          wrapMode: Text.Wrap; color: Color.accent; font.pixelSize: 13
        }
        RowLayout {
          Layout.fillWidth: true
          Text {
            Layout.fillWidth: true
            text: root.picking ? (root.selectedApp ? "Choose a key" : "Choose an app") : "Your shortcuts · " + root.rows.length
            color: Color.foreground; font.pixelSize: 15; font.bold: true
          }
          Button {
            text: root.picking ? "Back" : "+ Add shortcut"; focusable: true; bordered: true
            onClicked: { root.picking = !root.picking; root.selectedApp = null; search.text = ""; root.refreshApps() }
          }
        }
        TextField {
          id: search
          visible: root.picking && !root.selectedApp
          Layout.fillWidth: true
          placeholderText: "Search apps…"
          onTextChanged: root.refreshApps()
        }
        ColumnLayout {
          visible: root.picking && root.selectedApp !== null
          Layout.fillWidth: true
          Text {
            text: root.selectedApp ? root.selectedApp.name : ""
            textFormat: Text.PlainText; color: Color.accent; font.pixelSize: 18
          }
          TextField {
            id: shortcut
            Layout.fillWidth: true
            placeholderText: "Key, e.g. A or Shift+A"
            onAccepted: save.clicked()
          }
          Text { text: "Letters, digits, F1–F12, Return, Space or arrows."; color: Color.foreground; opacity: 0.65; font.pixelSize: 12 }
          Button {
            id: save
            text: "Save ✦ shortcut"; focusable: true; bordered: true
            enabled: !backend.running && shortcut.text.trim() !== ""
            onClicked: {
              var k = shortcut.text.trim().toUpperCase()
              if (root.state.shortcuts[k]) { root.error = "That key is already assigned. Remove its shortcut first."; return }
              root.request(["assign", k, root.selectedApp.id, root.selectedApp.name])
            }
          }
        }
        Controls.ScrollView {
          Layout.fillWidth: true
          Layout.fillHeight: true
          clip: true
          visible: !root.selectedApp
          ListView {
            id: list
            model: root.picking ? root.apps : root.rows
            spacing: 4
            delegate: Rectangle {
              required property var modelData
              width: list.width
              height: 52
              radius: 5
              color: index % 2 ? Qt.rgba(1, 1, 1, 0.035) : "transparent"
              required property int index
              RowLayout {
                anchors.fill: parent
                anchors.margins: 6
                spacing: 10
                Text {
                  visible: !root.picking
                  text: "✦ " + (modelData.key || "custom")
                  color: Color.accent; font.pixelSize: 13
                  Layout.preferredWidth: 106
                }
                Text {
                  Layout.fillWidth: true
                  text: modelData.name
                  textFormat: Text.PlainText
                  elide: Text.ElideRight
                  color: Color.foreground; font.pixelSize: 14
                }
                Button {
                  visible: root.picking || !modelData.external
                  text: root.picking ? "Choose" : "Remove"
                  focusable: true; enabled: !backend.running
                  onClicked: {
                    if (root.picking) { root.selectedApp = modelData; shortcut.text = ""; shortcut.forceActiveFocus() }
                    else root.request(["remove", modelData.key])
                  }
                }
                Text {
                  visible: !root.picking && !!modelData.external
                  text: "Config"; color: Color.foreground; opacity: 0.5; font.pixelSize: 11
                }
              }
            }
            Text {
              anchors.centerIn: parent
              visible: list.count === 0
              text: root.picking ? "No matching apps" : "Add your first app shortcut"
              color: Color.foreground; opacity: 0.6
            }
          }
        }
        Item { visible: root.selectedApp !== null; Layout.fillHeight: true }
        Text {
          Layout.fillWidth: true
          text: root.state.options !== null ? "Hyper setup is managed here." : (root.state.active ? "Hyper is already set up in your Hyprland config.\nRows marked Config are managed in that file." : "Setup preserves your other keyboard settings.")
          wrapMode: Text.WordWrap; color: Color.foreground; opacity: 0.55; font.pixelSize: 12
        }
        Button {
          visible: root.state.options !== null
          text: "Restore previous Caps Lock behavior"; focusable: true
          enabled: !backend.running
          onClicked: root.request(["restore"])
        }
      }
    }
  }
}
