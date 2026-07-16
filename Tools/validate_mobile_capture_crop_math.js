"use strict";

const assert = require("node:assert/strict");
const {
  calculateCoverCrop,
  calculateCaptureOutputSize
} = require("../Docs/app.js");

function close(actual, expected, tolerance = 1e-7) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} is not close to ${expected}`);
}

function assertInside(crop, sourceWidth, sourceHeight) {
  assert.ok(crop.sourceX >= 0);
  assert.ok(crop.sourceY >= 0);
  assert.ok(crop.sourceX + crop.sourceWidth <= sourceWidth + 1e-7);
  assert.ok(crop.sourceY + crop.sourceHeight <= sourceHeight + 1e-7);
}

const landscapeIntoPortrait = calculateCoverCrop(1920, 1080, 390, 620);
close(landscapeIntoPortrait.sourceHeight, 1080);
close(landscapeIntoPortrait.sourceWidth / landscapeIntoPortrait.sourceHeight, 390 / 620);
assertInside(landscapeIntoPortrait, 1920, 1080);

const portraitIntoPortrait = calculateCoverCrop(1080, 1920, 390, 620);
close(portraitIntoPortrait.sourceWidth, 1080);
close(portraitIntoPortrait.sourceWidth / portraitIntoPortrait.sourceHeight, 390 / 620);
assertInside(portraitIntoPortrait, 1080, 1920);

const exactAspect = calculateCoverCrop(900, 1200, 360, 480);
close(exactAspect.sourceX, 0);
close(exactAspect.sourceY, 0);
close(exactAspect.sourceWidth, 900);
close(exactAspect.sourceHeight, 1200);
assertInside(exactAspect, 900, 1200);

for (const [sourceWidth, sourceHeight, previewWidth, previewHeight] of [
  [4032, 3024, 390, 620],
  [3024, 4032, 390, 620],
  [1920, 1080, 844, 390],
  [1080, 1920, 390, 844]
]) {
  const crop = calculateCoverCrop(sourceWidth, sourceHeight, previewWidth, previewHeight);
  const output = calculateCaptureOutputSize(crop, 1800);
  assertInside(crop, sourceWidth, sourceHeight);
  assert.ok(output.width > 0 && output.height > 0);
  close(output.width / output.height, previewWidth / previewHeight, 0.002);
}

console.log("Mobile capture crop math validation passed.");
