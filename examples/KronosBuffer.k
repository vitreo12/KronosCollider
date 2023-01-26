Import Algorithm
Import Gen
Import IO

Main() {
    speed = Param:New("speed" #1)
	buf = Buffer:New("buf" #48000 * #120) ; Up to 2 minutes of mono (1 minute of stereo)
	bufFrames = Buffer:Frames(buf)
	bufSampleRate = Buffer:SampleRate(buf)
	scaledRate = #1 / (bufFrames / bufSampleRate)
	reader = Gen:Phasor(scaledRate * speed) * bufFrames
	Algorithm:Map(
		chan => Buffer:ReadHermite(buf reader chan)
		Algorithm:Count(#2 #0)
	)
}
