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
  property var catalog: []
  readonly property var library: bar && bar.shell ? bar.shell.appLibrary : null
  readonly property var rows: {
    var result = []
    var shortcuts = state.shortcuts || {}
    Object.keys(shortcuts).sort().forEach(function(key) {
      result.push({key: key, name: shortcuts[key].name, id: shortcuts[key].id, external: false})
    })
    return result.concat(state.external || []).map(function(row) {
      var app = root.appForShortcut(row)
      return {key: row.key, name: app ? app.name : row.name,
        description: app && app.name !== row.name ? row.name : "",
        icon: app ? app.icon : "", id: row.id, external: row.external}
    })
  }

  function appForShortcut(row) {
    function normalized(value) { return String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "") }
    var exact = catalog.filter(function(app) { return row.id ? app.id === row.id : normalized(app.name) === normalized(row.name) || normalized(app.id) === normalized(row.name) })
    if (exact.length === 1) return exact[0]
    // A short binding label can omit a vendor prefix, e.g. Chrome / Google Chrome.
    var suffix = catalog.filter(function(app) { return app.name.toLowerCase().endsWith(" " + String(row.name).toLowerCase()) })
    return suffix.length === 1 ? suffix[0] : null
  }
  function appRows(query) {
    return library ? library.sortedEntries(query).map(function(row) {
      var app = row.entry
      return {id: String(app.id), name: library.entryName(app), icon: String(app.icon || "")}
    }) : []
  }
  function refreshApps() {
    catalog = appRows("")
    apps = appRows(search.text)
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
    refreshApps()
    if (library) library.refreshIcons()
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
        }
        Toggle {
          Layout.fillWidth: true
          label: "Use Caps Lock as Hyper"
          description: root.state.active ? "On · Hold Caps Lock for ✦ shortcuts" : "Off · Caps Lock toggles uppercase letters"
          checked: !!root.state.active
          enabled: !backend.running
          onClicked: root.request([root.state.active ? "disable" : "enable"])
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
                Image {
                  Layout.preferredWidth: Style.font.iconLarge
                  Layout.preferredHeight: Style.font.iconLarge
                  fillMode: Image.PreserveAspectFit
                  sourceSize.width: width * Screen.devicePixelRatio
                  sourceSize.height: height * Screen.devicePixelRatio
                  source: root.library ? root.library.iconSource(modelData.icon || "") : ""
                  asynchronous: true
                }
                ColumnLayout {
                  Layout.fillWidth: true
                  spacing: 2
                  Text {
                    Layout.fillWidth: true
                    text: modelData.name
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: Color.foreground
                    font.family: Style.font.family
                    font.pixelSize: Style.font.heading
                    font.weight: Font.Medium
                  }
                  Text {
                    Layout.fillWidth: true
                    visible: !!modelData.description
                    text: modelData.description || ""
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: Color.foreground
                    opacity: 0.55
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                  }
                }
                Text {
                  visible: !root.picking
                  text: "✦ " + (modelData.key || "custom")
                  color: Color.accent
                  font.family: Style.font.family
                  font.pixelSize: 13
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
          text: "Turning Hyper off restores normal Caps Lock.\nYour shortcuts stay saved. Config rows come from Hyprland."
          wrapMode: Text.WordWrap; color: Color.foreground; opacity: 0.55; font.pixelSize: 12
        }

      }
    }
  }
}
