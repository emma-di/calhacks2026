import test from "node:test";
import assert from "node:assert/strict";
import { displayPiLevels, emptyPiLevels, failPiLevels, parsePiLevels, piLevelFraction, receivePiLevels } from "./piLevels.ts";

const sample = () => ({ schema_version:1, sample_rate:48000, channels:2, sequence:12, age_ms:20, connected:true,
  levels:[{channel:0,rms_dbfs:-30,peak_dbfs:-10,clip_fraction:0},{channel:1,rms_dbfs:-120,peak_dbfs:-110,clip_fraction:0}], error:null });

test("real stereo level parser keeps silent channels connected and distinct", () => {
  const value = parsePiLevels(sample());
  const display = displayPiLevels(receivePiLevels(emptyPiLevels(), value, 1000), 1100);
  assert.equal(display.status, "live");
  assert.equal(display.levels?.[0].rms_dbfs, -30);
  assert.equal(display.levels?.[1].rms_dbfs, -120);
  assert.equal(piLevelFraction(-120), 0);
});

test("parser rejects malformed, non-stereo or out-of-range level data", () => {
  for (const change of [{schema_version:2},{sample_rate:16000},{channels:1},{sequence:-1},{sequence:Infinity},
    {age_ms:-1},{age_ms:null},{levels:[]},{levels:[{...sample().levels[0],channel:1},sample().levels[1]]},{levels:[{channel:0,rms_dbfs:NaN,peak_dbfs:-10,clip_fraction:0},sample().levels[1]]},
    {levels:[{channel:0,rms_dbfs:-30,peak_dbfs:1,clip_fraction:0},sample().levels[1]]},
    {levels:[{channel:0,rms_dbfs:-30,peak_dbfs:-10,clip_fraction:2},sample().levels[1]]}]) {
    assert.throws(() => parsePiLevels({...sample(),...change}));
  }
  assert.throws(() => parsePiLevels(null));
});

test("server age and locally elapsed time clear stale bars", () => {
  const old = receivePiLevels(emptyPiLevels(), parsePiLevels({...sample(),age_ms:1400}), 1000);
  assert.equal(displayPiLevels(old,1050).status,"live");
  assert.deepEqual(displayPiLevels(old,1100),{status:"stale",levels:null});
});

test("repeated frozen sequence cannot keep a stale capture alive through successful HTTP polling", () => {
  const first = receivePiLevels(emptyPiLevels(),parsePiLevels(sample()),1000);
  const repeated = receivePiLevels(first,parsePiLevels({...sample(),age_ms:0}),2400);
  assert.equal(displayPiLevels(repeated,2500).status,"stale");
  const resumed = receivePiLevels(repeated,parsePiLevels({...sample(),sequence:13}),2600);
  assert.equal(displayPiLevels(resumed,2600).status,"live");
});

test("disconnect or failed transport immediately empties meters; a fresh response recovers", () => {
  const live = receivePiLevels(emptyPiLevels(),parsePiLevels(sample()),1000);
  const disconnected = receivePiLevels(live,parsePiLevels({...sample(),connected:false,levels:[],age_ms:null}),1100);
  assert.deepEqual(displayPiLevels(disconnected,1100),{status:"offline",levels:null});
  const failed = failPiLevels("Bridge disconnected");
  assert.deepEqual(displayPiLevels(failed,1100),{status:"offline",levels:null});
  assert.equal(displayPiLevels(receivePiLevels(failed,parsePiLevels(sample()),1200),1200).status,"live");
  assert.equal(displayPiLevels(emptyPiLevels(),0).status,"pending");
});

test("RMS scale remains bounded and expresses decibels rather than classification confidence", () => {
  assert.equal(piLevelFraction(-60),0);
  assert.equal(piLevelFraction(-30),0.5);
  assert.equal(piLevelFraction(0),1);
  assert.equal(piLevelFraction(10),1);
});
