// 友人戦（2026-10-02 ゆーしん「ポケモンバトルみたいに、相手と自分のやってることが合うように」）
// メンバーの battle.js の仕組み（makeFighter・turnOrder・act・endRound・renderBattle・askQte など）をそのまま使い、
// 「相手をコンピューターが動かす」ところだけを「相手のスマホで選んだ技を待つ」にかえたもの。battle.js には手を入れていない。
//
// 2人の画面で結果が同じになるように：
// - 乱数は、サーバーが決めた同じ「たね」から作る（Math.random は使わない）
// - 行動の順番・ダメージの計算は、番号の小さい方（lo）→大きい方（hi）の決まった並びで呼ぶ
// - タイミングバー（QTE）は、その技を出す人のスマホだけで押し、結果の倍率を相手にも送る
// - 連続攻撃のアニメ（battle.js の playCombo）は中で Math.random を使うので、その間だけ同じたねの乱数に差しかえる
// 2026-10-02 battle.js ef25461 に合わせた（ラウンドの上限なし・連続攻撃のアニメ・タイミングの帯の位置）
//
// 相手が抜けたとき（2026-10-02 ゆーしん「相手が切断中ですみたいな表示を」）：
// - 2人とも3秒ごとに「生きている合図」を送る。相手の合図が10秒来ないと「相手が切断中です」と残り時間を出す
// - 60秒以内に相手がページを開き直せば、サーバーに残っている2人の技とタイミングの結果から、同じところまで一気に再現して続きから
// - 60秒たっても戻らなければ、残った人の不戦勝
(function () {
  function seeded(seed) {   // mulberry32：同じたねなら、どの端末でも同じ数が同じ順で出る
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  async function send(m, body) {
    for (let i = 0; i < 5; i += 1) {   // 電波が悪くても何回か送り直す
      try {
        const r = await fetch('/api/pvp/act', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ match: m.id, token: m.token, ...body }) });
        if (r.ok) return true;
      } catch (e) {}
      await wait(800);
    }
    return false;
  }

  const GONE_SHOW = 10, GONE_LIMIT = 60;   // 秒
  const FORFEIT_WIN = { forfeit: "win" }, FORFEIT_LOSE = { forfeit: "lose" };

  async function state(m) {
    const s = await (await fetch(`/api/pvp/state?match=${m.id}&token=${encodeURIComponent(m.token)}`)).json();
    return s.ok ? s : null;
  }

  let onLeave = null;   // 「対戦から抜ける」を押したときにすること（試合ごとに playPvp が決める）
  // 「相手が切断中です」の表示（バトルの画面の上に重ねる）
  function goneOverlay(left) {
    let el = document.getElementById("pvp-gone");
    if (left == null) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement("div");
      el.id = "pvp-gone";
      el.innerHTML = `<div class="gone-box"><div class="dots"><i></i><i></i><i></i></div><h2>相手が切断中です</h2>
        <p>相手が戻ってくるのを待っています。<br>戻ってきたら、続きから再開します。</p><p class="gone-left"></p>
        <button class="ghost gone-leave" type="button">対戦から抜ける</button></div>`;
      document.body.appendChild(el);
      // 待たずに抜ける（2026-10-02 ゆーしん）。抜けた側が先に切断したので、記録上はこちらの不戦勝にしてパスポートへ戻る
      el.querySelector(".gone-leave").onclick = () => { if (onLeave) onLeave(); };
    }
    el.querySelector(".gone-left").textContent = `あと ${Math.max(0, Math.ceil(left))} 秒待っても戻らなければ、対戦はここまでになります`;
  }

  // 条件がそろうまで、0.7秒ごとに試合の状態を見に行く。途中で不戦勝・不戦敗が決まったら、その印を返す
  async function until(m, check) {
    while (true) {
      if (m.ended) return m.ended;
      try {
        const s = await state(m);
        const v = s ? check(s) : undefined;
        if (v !== undefined && v !== null) return v;
      } catch (e) {}
      await wait(700);
    }
  }

  // 切断の見張り役：対戦のあいだずっと、1.5秒ごとに相手の合図を見る（2026-10-02 自分が技を選んでいる間も見るように直した。
  // 前は「相手を待っている間」しか見ておらず、残った人がページを開き直すまで「切断中」が出なかった）
  function watch(m, onEnd) {
    let busy = false;
    const timer = setInterval(async () => {
      if (m.ended || busy) return;
      busy = true;
      try {
        const s = await state(m);
        if (s && !m.ended) {
          if (s.forfeit === m.theirs) { m.ended = FORFEIT_LOSE; goneOverlay(null); onEnd(); }   // 自分が抜けている間に相手の不戦勝になっていた
          else {
            const away = s.now - Math.max(s.created || 0, (s.seen || {})[m.theirs] || 0);
            if (away > GONE_LIMIT) { m.ended = FORFEIT_WIN; goneOverlay(null); send(m, { kind: "forfeit" }); onEnd(); }
            // 相手が画面を閉じた・ホームに戻ったときはすぐ、合図が止まっただけ（電波など）のときは10秒で「切断中」
            else goneOverlay(away > GONE_SHOW || (s.away || {})[m.theirs] ? GONE_LIMIT - away : null);
          }
        }
      } catch (e) {}
      busy = false;
    }, 1500);
    return () => { clearInterval(timer); goneOverlay(null); };
  }

  async function playPvp(m) {
    // m = { id, token, seed, side: "lo"|"hi", me, meMonth, foe, foeMonth }
    const rng = seeded(m.seed);
    const player = makeFighter("あなた", m.me, m.meMonth);
    const enemy = makeFighter("相手", m.foe, m.foeMonth);
    const lo = m.side === "lo" ? player : enemy, hi = m.side === "lo" ? enemy : player;
    const mine = m.side, theirs = m.side === "lo" ? "hi" : "lo";
    m.theirs = theirs;
    // 生きている合図：3秒ごと（画面を閉じたり、ほかのアプリに切り替えたりすると止まる）
    send(m, { kind: "ping" });
    const beat = setInterval(() => { if (!finished && !document.hidden) send(m, { kind: "ping" }); else if (finished) clearInterval(beat); }, 3000);
    // 自分が画面を閉じた・ホーム画面に戻った・ほかのアプリに切り替えたら、すぐ相手に知らせる。戻ってきたらすぐ合図
    const awayBeacon = () => {
      if (finished) return;
      navigator.sendBeacon("/api/pvp/act", new Blob([JSON.stringify({ match: m.id, token: m.token, kind: "away" })], { type: "application/json" }));
    };
    const onVis = () => { if (document.hidden) awayBeacon(); else if (!finished) send(m, { kind: "ping" }); };
    document.addEventListener("visibilitychange", onVis);
    window.addEventListener("pagehide", awayBeacon);
    // 開き直したとき：サーバーに残っている2人の技とタイミングの結果（これまでのぶん）
    let hist = { picks: {}, qte: {} };
    try { hist = (await state(m)) || hist; } catch (e) {}
    let endNow = () => {};
    const ended = new Promise((resolve) => { endNow = resolve; });
    const unwatch = watch(m, () => endNow(m.ended));
    onLeave = async () => {
      m.ended = FORFEIT_WIN; finished = true;
      await send(m, { kind: "forfeit" });
      location.href = "/r/" + m.token;
    };
    const realWait = window.wait;
    const fastWait = () => Promise.resolve();
    shownHp = null;
    Sfx.ensure();
    const log = [`相手は${enemy.type}（${enemy.month}月）`];
    let round = 1, finished = false;
    const view = (extra) => ({ player, enemy, log: log.slice(), round, waiting: false, qte: false, finished, phaseText: "", ...extra });

    function lost(text) {   // 相手の通信が切れたとき
      finished = true;
      renderBattle(view({ phaseText: text, finished: true }));
    }

    while (alive(player) && alive(enemy)) {
      // 開き直したときは、2人とも選び終わっているラウンドを一気に再現する（アニメを待たない）
      const known = hist.picks[String(round)] || {};
      const replay = known[mine] != null && known[theirs] != null;
      window.wait = replay ? fastWait : realWait;
      // 1. 自分の技を選ぶ（選び方は battle.js と同じ）。開き直す前に選んでいたら、それを使う
      if (known[mine] == null) renderBattle(view({ command: true, waiting: true, phaseText: "行動を選ぶ" }));
      const picked = known[mine] != null ? Number(known[mine]) : await Promise.race([ended, new Promise((resolve) => {
        document.querySelectorAll("[data-skill]").forEach((button) => {
          button.onclick = () => {
            const skill = player.skills[Number(button.dataset.skill)];
            const usable = canUse(player, skill);
            const close = showSheet(`
              <h2>${escapeHtml(skill.name)}</h2>
              <p>${escapeHtml(skillBlurb(skill.name))}</p>
              ${usable ? `<button class="primary" id="use-skill" type="button">これに決める</button>` : `<p class="detail">今は使えない</p>`}
              <button class="ghost" data-close type="button">戻る</button>`);
            const use = document.getElementById("use-skill");
            if (use) use.onclick = () => { close(); resolve(Number(button.dataset.skill)); };
          };
        });
      })]);
      if (picked === FORFEIT_WIN || picked === FORFEIT_LOSE) {
        const sheet = document.getElementById("sheet"), back = document.getElementById("backdrop");
        if (sheet) sheet.hidden = true; if (back) back.hidden = true;
        lost(picked === FORFEIT_WIN ? "相手がもどってこなかったので、対戦はここまでになったよ" : "はなれている間に、対戦が終わったよ"); break;
      }
      if (known[mine] == null) { Sfx.select(); await send(m, { kind: "pick", round, value: picked }); }

      // 2. 相手が選ぶのを待つ
      renderBattle(view({ phaseText: "相手が技を選んでいます…", picks: { player: player.skills[picked].name, enemy: "考え中…" } }));
      const foePick = known[theirs] != null ? Number(known[theirs]) : await until(m, (s) => (s.picks[String(round)] || {})[theirs]);
      if (foePick === FORFEIT_WIN) { lost("相手がもどってこなかったので、対戦はここまでになったよ"); break; }
      if (foePick === FORFEIT_LOSE) { lost("はなれている間に、対戦が終わったよ"); break; }
      const plan = { [mine]: player.skills[picked], [theirs]: enemy.skills[foePick] };

      // 3. 2人の技を同時に見せる
      renderBattle(view({ phaseText: "おたがいの技が決まった！", picks: { player: plan[mine].name, enemy: plan[theirs].name } }));
      await wait(1100);

      // 4. 順番に行動する（2人の画面で同じ順・同じ乱数）
      const order = turnOrder(lo, hi, rng);
      let broken = false;
      for (let i = 0; i < order.length; i += 1) {
        const actor = order[i];
        const target = actor === lo ? hi : lo;
        if (!alive(actor) || !alive(target)) break;
        const skill = skillToAct(actor, plan[actor === lo ? "lo" : "hi"], log);
        if (!skill) {
          renderBattle(view({ phaseText: `${actor.side}は動けなかった` }));
          await wait(700);
          continue;
        }
        let qte = 1;
        const savedQte = hist.qte[`${round}-${i}`];
        if (skill.qte && actor === player && savedQte != null) {
          qte = Number(savedQte);   // 開き直す前に押していたタイミングの結果
        } else if (skill.qte && actor === player) {
          const qteLayout = qteWindow(player.type === "鳥類");   // 帯の位置は自分の画面だけのこと（結果の倍率だけ相手に送る）
          renderBattle(view({ qte: true, qteLayout, phaseText: `${skill.name}：緑の帯で止める` }));
          const result = await Promise.race([ended, askQte(auraSum(player, "qteSlow") > 0, qteLayout)]);
          if (result === FORFEIT_WIN || result === FORFEIT_LOSE) { broken = result; break; }
          qte = result.mult;
          Sfx.qte(result.label);
          const stop = document.getElementById("qte-stop");
          if (stop) stop.textContent = result.label;
          log.push(`QTE ${result.label}`);
          await send(m, { kind: "qte", round, step: i, value: qte });
          await wait(380);
        } else if (skill.qte) {
          renderBattle(view({ phaseText: `相手が${skill.name}のタイミングを合わせています…` }));
          const v = await until(m, (s) => s.qte[`${round}-${i}`]);
          if (v === FORFEIT_WIN || v === FORFEIT_LOSE) { broken = v; break; }
          qte = Number(v);
        } else if (actor !== player) {
          renderBattle(view({ phaseText: "相手の行動" }));
          await wait(450);
        }
        if (skill.power && skill.hits > 1) {
          // 連続攻撃：1発ずつアニメで見せる。中の乱数を同じたねのものにする
          const original = Math.random;
          Math.random = rng;
          try { await playCombo(actor, target, skill, qte, log, view); } finally { Math.random = original; }
          finishAct(actor, target, skill, log);
        } else {
          const mark = log.length;
          act(actor, target, skill, qte, rng, log);
          renderBattle(view({ phaseText: `${actor.side}の${skill.name}`, actor: actor.side,
            fxCrit: fxCrit(log.slice(mark)), fxCut: fxCut(log.slice(mark)) }));
          await wait(900);
        }
      }
      if (broken) { lost(broken === FORFEIT_WIN ? "相手がもどってこなかったので、対戦はここまでになったよ" : "はなれている間に、対戦が終わったよ"); break; }
      if (alive(player) && alive(enemy)) {
        const mark = log.length;
        endRound(lo, hi, log);
        round += 1;
        if (log.length > mark) {
          renderBattle(view({ phaseText: "ラウンドの終わり", fxCrit: fxCrit(log.slice(mark)) }));
          await wait(700);
        }
      } else break;
    }

    window.wait = realWait;
    clearInterval(beat);
    unwatch();
    document.removeEventListener("visibilitychange", onVis);
    window.removeEventListener("pagehide", awayBeacon);
    if (!finished) {
      finished = true;
      let phaseText = "引き分け";
      if (player.hp > 0 && enemy.hp <= 0) phaseText = "勝ち！";
      else if (enemy.hp > 0 && player.hp <= 0) phaseText = "負け…";
      player.hp = Math.max(0, player.hp);
      enemy.hp = Math.max(0, enemy.hp);
      shownHp = { player: player.hp, enemy: enemy.hp };
      renderBattle(view({ phaseText, finished: true }));
      send(m, { kind: "done" });
    }
  }

  window.playPvp = playPvp;
})();
