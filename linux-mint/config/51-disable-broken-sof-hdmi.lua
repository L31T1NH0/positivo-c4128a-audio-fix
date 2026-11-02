-- The Positivo C4128A-15 exposes HDMI PCM devices 5, 6 and 7 even with no
-- monitor connected. Probing them makes the SOF DSP return -EIO and leaves
-- analog playback unusable. Use a dedicated ACP profile containing PCM 0
-- only. Ignore the falsely asserted analog headphone jack for this test.
local positivo_essx8336 = {
  matches = {
    {
      { "device.name", "equals", "alsa_card.pci-0000_00_0e.0-platform-sof-essx8336" },
    },
  },
  apply_properties = {
    ["api.alsa.use-ucm"] = false,
    ["device.profile-set"] = "@HOME@/.config/positivo-audio/profile.conf",
  },
}

table.insert(alsa_monitor.rules, positivo_essx8336)

table.insert(alsa_monitor.rules, {
  matches = {
    { { "node.name", "equals", "alsa_output.pci-0000_00_0e.0-platform-sof-essx8336.positivo-speakers" } },
  },
  apply_properties = {
    ["node.description"] = "Alto-falantes internos (Positivo)",
    ["node.nick"] = "Alto-falantes internos",
    -- The SOF PCM can stall when reopened after playback becomes idle.
    ["session.suspend-timeout-seconds"] = 0,
    ["node.pause-on-idle"] = false,
  },
})
