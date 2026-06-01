// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;
import "forge-std/Script.sol";

interface ISafe {
    function setup(
        address[] calldata _owners,
        uint256 _threshold,
        address to,
        bytes calldata data,
        address fallbackHandler,
        address paymentToken,
        uint256 payment,
        address payable paymentReceiver
    ) external;
}

interface ISafeProxyFactory {
    function createProxyWithNonce(
        address _singleton,
        bytes memory initializer,
        uint256 saltNonce
    ) external returns (address);
}

contract DeploySafeCREATE2 is Script {
    address constant SAFE_SINGLETON = 0x29fcB43b46531BcA003ddC8FCB67FFE91900C762; // SafeL2
    address constant SAFE_PROXY_FACTORY = 0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67;
    address constant FALLBACK_HANDLER = 0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99;

    uint256 constant MONAD_MAINNET_CHAIN_ID = 143;
    uint256 constant MONAD_TESTNET_CHAIN_ID = 10143;

    function run() external returns (address) {
        address owner1 = vm.envAddress("OWNER_1");
        address owner2 = vm.envAddress("OWNER_2");
        address owner3 = vm.envAddress("OWNER_3");

        address[] memory owners = new address[](3);
        owners[0] = owner1;
        owners[1] = owner2;
        owners[2] = owner3;

        bytes memory initializer = abi.encodeWithSelector(
            ISafe.setup.selector,
            owners,              // _owners
            2,                   // _threshold (2 of 3)
            address(0),          // to
            "",                  // data
            FALLBACK_HANDLER,    // fallbackHandler
            address(0),          // paymentToken
            0,                   // payment
            payable(0)           // paymentReceiver
        );

        vm.startBroadcast();

        // Deterministic if SALT_NONCE is fixed; default derives from owners + chainId
        uint256 saltNonce = vm.envOr(
            "SALT_NONCE",
            uint256(keccak256(abi.encode(owners, block.chainid)))
        );

        address proxy = ISafeProxyFactory(SAFE_PROXY_FACTORY).createProxyWithNonce(
            SAFE_SINGLETON,
            initializer,
            saltNonce
        );

        string memory safePrefix;
        if (block.chainid == MONAD_MAINNET_CHAIN_ID) {
            safePrefix = "monad";
        } else if (block.chainid == MONAD_TESTNET_CHAIN_ID) {
            safePrefix = "monad-testnet";
        } else {
            revert("Unsupported chain");
        }

        console.log("Safe deployed at:", proxy);
        console.log(
            string.concat("Access: https://app.safe.global/home?safe=", safePrefix, ":"),
            proxy
        );

        vm.stopBroadcast();
        return proxy;
    }
}