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
  property bool statusLoaded: false
  readonly property color statusColor: state.active ? Color.accent : foreground
  readonly property string setupStatus: !statusLoaded ? "Checking keyboard…" : (state.active ? "Set up · ✦ Hyper enabled" : "Off · Normal Caps Lock")
  property var conflicts: []
  property bool picking: false
  property string action: "status"
  property var selectedApp: null
  property var apps: []
  property var catalog: []
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property color foreground: bar ? bar.foreground : Color.foreground
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
    conflicts = []
    action = args[0]
    backend.command = ["python3", Qt.resolvedUrl("hyper.py").toString().replace(/^file:\/\//, "")].concat(args)
    backend.running = true
  }
  onOpenedChanged: if (opened) {
    picking = false
    selectedApp = null
    conflicts = []
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
            root.statusLoaded = true
            if (root.action === "assign" || root.action === "overwrite") { root.picking = false; root.selectedApp = null }
          }
          else { root.error = result.error; root.conflicts = result.conflicts || [] }
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
    contentHeight: panel.fittedContentHeight(Style.space(690))

    FocusScope {
      id: content
      anchors.fill: parent
      Keys.onEscapePressed: {
        if (root.picking) { root.picking = false; root.selectedApp = null }
        else root.close()
      }
      ColumnLayout {
        anchors.fill: parent
        spacing: Style.space(10)
        Item {
          Layout.fillWidth: true
          implicitHeight: Math.max(headerLabels.implicitHeight, headerActions.implicitHeight)

          Item {
            id: headerIcon
            width: Style.font.display
            height: width
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            Text {
              anchors.centerIn: parent
              text: "✦"
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.display * 2.1
            }
            Rectangle {
              width: Math.max(5, parent.width * 0.34)
              height: width
              radius: width / 2
              anchors.right: parent.right
              anchors.bottom: parent.bottom
              color: root.statusColor
              border.width: 1
              border.color: Color.popups.background
            }
          }

          Column {
            id: headerLabels
            anchors.left: headerIcon.right
            anchors.leftMargin: Style.space(14)
            anchors.right: headerActions.left
            anchors.rightMargin: Style.space(10)
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(2)

            Text {
              width: parent.width
              textFormat: Text.PlainText
              text: "Hyper"
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.title
              font.bold: true
              elide: Text.ElideRight
            }
            Text {
              width: parent.width
              textFormat: Text.PlainText
              text: root.setupStatus
              color: root.statusColor
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
              font.bold: true
              elide: Text.ElideRight
            }
          }

          Row {
            id: headerActions
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(4)
            ToggleSwitch {
              checked: !!root.state.active
              busy: backend.running || !root.statusLoaded
              activeFocusOnTab: true
              Accessible.name: "Use Caps Lock as Hyper"
              Accessible.role: Accessible.CheckBox
              Accessible.checked: checked
              onToggled: if (!busy) root.request([root.state.active ? "disable" : "enable"])
              Keys.onSpacePressed: toggled()
              Keys.onReturnPressed: toggled()
            }
          }
        }
        PanelSeparator {
          Layout.fillWidth: true
          foreground: root.foreground
        }
        Text {
          Layout.fillWidth: true
          visible: root.error !== ""
          text: root.error; textFormat: Text.PlainText
          wrapMode: Text.Wrap; color: Color.accent; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
        }
        RowLayout {
          Layout.fillWidth: true
          Text {
            Layout.fillWidth: true
            text: root.picking ? (root.selectedApp ? "Choose a key" : "Choose an app") : "Your shortcuts · " + root.rows.length
            color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body; font.bold: true
          }
          Button {
            fontFamily: root.fontFamily
            fontSize: Style.font.bodySmall
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
            textFormat: Text.PlainText; color: Color.accent; font.family: root.fontFamily; font.pixelSize: Style.font.subtitle
          }
          TextField {
            id: shortcut
            Layout.fillWidth: true
            placeholderText: "Key, e.g. A or Shift+A"
            onTextChanged: { root.conflicts = []; root.error = "" }
            onAccepted: if (save.enabled) save.clicked()
          }
          Text { text: "Letters, digits, F1–F12, Return, Space or arrows."; color: root.foreground; opacity: 0.65; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
          Button {
            fontFamily: root.fontFamily
            fontSize: Style.font.bodySmall
            id: save
            text: "Save ✦ shortcut"; focusable: true; bordered: true
            enabled: !backend.running && shortcut.text.trim() !== ""
            onClicked: {
              root.request(["assign", shortcut.text, root.selectedApp.id, root.selectedApp.name])
            }
          }
          Button {
            visible: root.conflicts.length > 0
            text: "Overwrite"
            fontFamily: root.fontFamily
            fontSize: Style.font.bodySmall
            focusable: true
            bordered: true
            enabled: !backend.running
            onClicked: root.request(["overwrite", shortcut.text, root.selectedApp.id, root.selectedApp.name, JSON.stringify(root.conflicts)])
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
            spacing: Style.space(4)
            delegate: Rectangle {
              required property var modelData
              width: list.width
              height: 52
              radius: 5
              color: appMouse.containsMouse || activeFocus ? Style.hoverFillFor(root.foreground, Color.accent) : (index % 2 ? Qt.rgba(1, 1, 1, 0.035) : "transparent")
              required property int index
              activeFocusOnTab: root.picking
              function chooseApp() {
                if (!root.picking || backend.running) return
                root.selectedApp = modelData
                root.conflicts = []
                root.error = ""
                shortcut.text = ""
                shortcut.forceActiveFocus()
              }
              Keys.onReturnPressed: chooseApp()
              Keys.onSpacePressed: chooseApp()
              MouseArea {
                id: appMouse
                anchors.fill: parent
                enabled: root.picking && !backend.running
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: parent.chooseApp()
              }
              RowLayout {
                anchors.fill: parent
                anchors.margins: 6
                spacing: Style.space(10)
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
                  spacing: Style.space(2)
                  Text {
                    Layout.fillWidth: true
                    text: modelData.name
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: root.foreground
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.body
                    font.bold: true
                  }
                  Text {
                    Layout.fillWidth: true
                    visible: !!modelData.description
                    text: modelData.description || ""
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: root.foreground
                    opacity: 0.55
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.caption
                  }
                }
                Text {
                  visible: !root.picking
                  text: "✦ " + (modelData.key || "custom")
                  color: Color.accent
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                }
                Button {
                  fontFamily: root.fontFamily
                  fontSize: Style.font.bodySmall
                  visible: !root.picking
                  text: "Remove"
                  focusable: true
                  enabled: !backend.running
                  onClicked: root.request(["remove", modelData.key])
                }
              }
            }
            Text {
              anchors.centerIn: parent
              visible: list.count === 0
              text: root.picking ? "No matching apps" : "Add your first app shortcut"
              color: root.foreground; opacity: 0.6
            }
          }
        }
        Item { visible: root.selectedApp !== null; Layout.fillHeight: true }
        Text {
          Layout.fillWidth: true
          text: "Turning Hyper off restores normal Caps Lock.\nYour shortcuts stay saved."
          wrapMode: Text.WordWrap; color: root.foreground; opacity: 0.55; font.family: root.fontFamily; font.pixelSize: Style.font.caption
        }

      }
    }
  }
}
