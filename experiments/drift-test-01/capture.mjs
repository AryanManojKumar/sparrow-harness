import { chromium } from 'playwright';
const OUT = '/home/vo-01/Desktop/Prompts/Harness/projects/drift-test/shots';
const b = await chromium.launch();
for (const [name, w, h] of [['desktop',1440,900],['mobile',390,844]]) {
  const p = await b.newPage({ viewport:{width:w,height:h}, deviceScaleFactor:2 });
  await p.goto('http://localhost:4321/', { waitUntil:'networkidle' });
  // Scroll the whole page so every whileInView entrance animation fires,
  // otherwise below-the-fold sections capture at opacity 0.
  await p.evaluate(async () => {
    const step = window.innerHeight / 2;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise(r => setTimeout(r, 120));
    }
    window.scrollTo(0, 0);
    await new Promise(r => setTimeout(r, 300));
  });
  await p.waitForTimeout(800);
  await p.screenshot({ path:`${OUT}/${name}-full.png`, fullPage:true });
  console.log(name, 'ok');
  await p.close();
}
await b.close();
