import QtQuick
import QtTest
import Quickshell.Io
import "../../../../shell/plugins/panels/dropbox"

TestCase {
  name: "DropboxLifecycle"
  property var service: null
  Component { id: factory; Service {} }
  function find(arg) {
    for (var p of ProcessRegistry.processes)
      if (p.command.indexOf(arg) !== -1) return p
    return null
  }
  function status(running) {
    return JSON.stringify({ok: true, installed: true, authenticated: true,
      running: running, accountPath: "/dropbox", statusText: running ? "Up to date" : "Stopped"})
  }
  function init() {
    service = factory.createObject(this)
    wait(1)
    find("--quick").complete(0, status(true), "")
  }
  function cleanup() { service.destroy(); wait(1) }
  function test_noClosedInventory() {
    compare(find("--inventory"), null)
    for (var i = 0; i < 60; i++) {
      service.refresh()
      find("--quick").complete(0, status(true), "")
    }
    compare(find("--inventory"), null)
  }
  function test_controlsDuringInventory() {
    service.detailsWanted = true
    service.refresh(true)
    verify(find("--inventory").running)
    service.pause()
    compare(service.active, false)
    find("--quick").complete(0, status(true), "") // stale pre-pause result
    compare(service.active, false)
    find("stop").complete(0, "", "")
    find("--quick").complete(0, status(true), "") // daemon still settling
    compare(service.active, false)
    service.quickRefresh()
    find("--quick").complete(0, status(false), "")
    compare(service._desired, -1)
    service.resume()
    compare(service.active, true)
    find("start").complete(0, "", "")
    find("--quick").complete(0, status(true), "")
    compare(service._desired, -1)
    verify(find("--inventory").running)
    find("--inventory").complete(0, JSON.stringify({ok: true, accountPath: "/dropbox", usedBytes: 42}), "")
    compare(service.usedBytes, 42)
    compare(service.active, true)
    service.refresh()
    verify(!find("--inventory").running) // cached for five minutes
  }
  function test_controlFailure() {
    service.pause()
    find("stop").complete(1, "", "failed to stop")
    compare(service.active, true)
    compare(service.actionStatus, "failed to stop")
  }
}
