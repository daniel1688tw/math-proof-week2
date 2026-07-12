# 自我驗證教學端對端

## A. 逐步教學（A6，提示梯 2 條全數耗盡）

**助教**（phase=None）：先估一下 $2^n$ 的下界。用二項式定理展開 $(1+1)^n$，你能取到哪個最簡單的正項？

**學生**：我不知道怎麼開始。

**助教**（phase=None walk_idx=None walk_active=None）：換個角度：$2^n$ 是指什麼樣的量級？

**學生**：還是想不出來。

**助教**（phase=None walk_idx=None walk_active=None）：那試著寫出 $(1+1)^n$ 的前幾項，看看能湊出什麼下界。

**學生**：嗯…還是不會。

**助教**（phase=None walk_idx=None walk_active=None）：換個方式：$2^n$ 與 $n$ 相比，誰增長更快？

**學生**：真的想不到，再提示我。

**助教**（phase=None walk_idx=None walk_active=None）：這裡要用「二項式定理」。展開 $(1+1)^n$ 後，你能取到一個含 $n^2$ 項的下界嗎？

**學生**：我還是不會。

**助教**（phase=None walk_idx=None walk_active=None）：換個角度：$2^n$ 的最小值是多少？

**學生**：完全沒頭緒，我真的不會。

**助教**（phase=walkthrough walk_idx=0 walk_active=True）：那我直接告訴你：$2^n\ge\binom{n}{2}=\frac{n(n-1)}2$（$n\ge2$）。這個下界對你有幫助嗎？

**學生**：喔喔，這一步我懂了。

**助教**（phase=walkthrough walk_idx=1 walk_active=True）：很好。有了這個下界，你會怎麼把 $\frac{n}{2^n}$ 塞進夾擠？

**學生**：聽不懂這步。

**助教**（phase=walkthrough walk_idx=2 walk_active=True）：換個說法：由 $2^n\ge\frac{n(n-1)}2$，你能得到 $\frac{n}{2^n}$ 的上界是什麼？

**學生**：這樣講我懂了！

**助教**（phase=walkthrough walk_idx=3 walk_active=True）：對。最後用夾擠定理，$\frac{2}{n-1}\to0$ 就逼出答案。 $\lim_{n\to\infty}\dfrac{2}{n-1}$ 等於什麼？

**學生**：好，我懂整個思路了。

**助教**（phase=writeup_request walk_idx=4 walk_active=False）：很好。現在請你自己把完整的證明寫出來，我會審閱。


## B. 同學模式（unverified，含質疑反省）

**助教**（phase=None）：先說好：這題我自己也沒有把握，我們當同學一起想，我的想法你要幫忙把關。 先想：若 $f$ 是恆等函數 $f(x)=x$，它滿足條件嗎？

**學生**：我猜不動點集合就是 f 的值域，對嗎？

**助教**（phase=None walk_idx=None walk_active=None）：那值域本身是不是閉區間？

**學生**：你錯了吧，值域不一定是區間吧？

**助教**（phase=peer_reflect walk_idx=None walk_active=None）：對，我剛才犯了這個錯：不動點集合未必是值域，值域也不一定非閉不可。改用什麼方法？

**學生**：嗯，那我們先證非空好了，你覺得從哪裡下手？

**助教**（phase=None walk_idx=None walk_active=None）：用 Brouwer 不動點定理？但那需要 $f$ 是緊緻凸集上的連續函數，這裡的 $[0,1]$ 是緊緻的，但值域未必是凸的。
