/**
 * 1inch Fusion Order Builder (same-chain gasless swap)
 *
 * Reads input JSON from stdin (provided by Python exports.py),
 * builds a FusionOrder with proper extension encoding using @1inch/fusion-sdk,
 * and writes { typedData, orderStruct, extension, orderHash } to stdout.
 *
 * Stdin JSON fields:
 *   quoteJson        - full quote response from /fusion/quoter/v2.0/{chainId}/quote/receive
 *   fromTokenAddress - source token address
 *   toTokenAddress   - destination token address (native → WETH handled automatically)
 *   walletAddress    - maker EVM address
 *   chainId          - numeric chain ID
 *   preset           - "fast"|"medium"|"slow"
 *
 * Stdout: { typedData, orderStruct, extension, orderHash } | { error, stack }
 */

'use strict';

const {
    FusionOrder,
    Address,
    AuctionDetails,
    Whitelist,
    SurplusParams,
    CHAIN_TO_WRAPPER,
} = require('@1inch/fusion-sdk');

const NATIVE = '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee';

function resolveTokenAddress(addr, chainId) {
    /** Replace native ETH placeholder with wrapped version (required by FusionOrder). */
    if (addr.toLowerCase() === NATIVE) {
        const wrapper = CHAIN_TO_WRAPPER[String(chainId)];
        if (!wrapper) throw new Error(`No wrapper token for chainId ${chainId}`);
        return wrapper.toString();
    }
    return addr;
}

async function main() {
    let raw = '';
    process.stdin.setEncoding('utf8');
    for await (const chunk of process.stdin) raw += chunk;

    let input;
    try {
        input = JSON.parse(raw);
    } catch (e) {
        process.stdout.write(JSON.stringify({ error: 'Invalid JSON input: ' + e.message }));
        process.exit(1);
    }

    const {
        quoteJson,
        fromTokenAddress,
        toTokenAddress,
        walletAddress,
        chainId,
        preset: presetName,
    } = input;

    try {
        const recommended = quoteJson.recommended_preset || 'fast';
        const presetKey = presetName || recommended;
        const presetData = quoteJson.presets[presetKey] || quoteJson.presets[recommended];

        if (!presetData) throw new Error(`Preset '${presetKey}' not found in quote`);

        const settlementAddress = quoteJson.settlementAddress;
        const whitelist = quoteJson.whitelist || [];
        const now = BigInt(Math.floor(Date.now() / 1000));

        // AuctionDetails — all numeric fields must be BigInt
        const startAuctionIn = BigInt(presetData.startAuctionIn || 30);
        const auctionDuration = BigInt(presetData.auctionDuration || 180);
        const initialRateBump = BigInt(presetData.initialRateBump || 0);
        const points = (presetData.points || []).map(p => ({
            coefficient: Number(p.coefficient || 0),
            delay: Number(p.delay || 0),
        }));

        const ad = new AuctionDetails({
            startTime: now + startAuctionIn,
            duration: auctionDuration,
            initialRateBump,
            points,
        });

        // Whitelist — each item needs {address, allowFrom: BigInt}
        const wl = Whitelist.new(
            now,
            whitelist.map(addr => ({
                address: new Address(addr),
                allowFrom: now,
            }))
        );

        // Resolve token addresses (native → wrapped)
        const makerAssetAddr = fromTokenAddress;
        const takerAssetAddr = resolveTokenAddress(toTokenAddress, chainId);
        const unwrapWETH = toTokenAddress.toLowerCase() === NATIVE;

        // Amount from quote
        const endAmount = presetData.auctionEndAmount || quoteJson.toTokenAmount;

        const order = new FusionOrder(
            new Address(settlementAddress),
            {
                makerAsset: new Address(makerAssetAddr),
                takerAsset: new Address(takerAssetAddr),
                makingAmount: BigInt(quoteJson.fromTokenAmount),
                takingAmount: BigInt(endAmount),
                maker: new Address(walletAddress),
            },
            ad,
            wl,
            SurplusParams.NO_FEE,
            {
                allowPartialFills: true,
                allowMultipleFills: true,
                unwrapWETH,
            }
        );

        const orderHash = order.getOrderHash(chainId);
        const typedData = order.getTypedData(chainId);
        const extension = order.extension.encode();
        const built = order.build();

        // Serialize — BigInt → string for JSON transport
        const orderStruct = JSON.parse(
            JSON.stringify(built, (k, v) => typeof v === 'bigint' ? v.toString() : v)
        );

        process.stdout.write(JSON.stringify({
            typedData,
            orderStruct,
            extension,
            orderHash,
        }));
    } catch (e) {
        process.stdout.write(JSON.stringify({
            error: e.message,
            stack: e.stack ? e.stack.split('\n').slice(0, 5).join('\n') : '',
        }));
        process.exit(1);
    }
}

main().catch(e => {
    process.stdout.write(JSON.stringify({ error: e.message }));
    process.exit(1);
});
